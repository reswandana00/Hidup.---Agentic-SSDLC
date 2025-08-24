"""
Shared utilities and tools for all agents.
Contains common functions, memory management, and tool factories.
"""
import os
import json
import time
import random
import re
from typing import List

from dotenv import load_dotenv
from pydantic_ai import RunContext
from pydantic_ai.models.google import GoogleModel
from pydantic_ai.providers.google import GoogleProvider
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm

console = Console()

# ==================================================================================================
# SETUP AND UTILITIES
# ==================================================================================================

def parse_google_api_error(error_str):
    """Parse Google API error untuk mendapatkan retry delay dan pesan yang user-friendly."""
    try:
        # Cek apakah ini error quota/rate limit
        if "RESOURCE_EXHAUSTED" in str(error_str) or "429" in str(error_str):
            # Extract retry delay dari error message
            retry_match = re.search(r"'retryDelay': '(\d+)s'", str(error_str))
            if retry_match:
                retry_seconds = int(retry_match.group(1))
            else:
                retry_seconds = 60  # Default 60 detik jika tidak ditemukan
            
            return {
                "is_quota_error": True,
                "retry_delay": retry_seconds,
                "user_message": f"Limit penggunaan AI tercapai, tunggu {retry_seconds} detik...",
                "should_retry": True
            }
        
        # Cek error lainnya yang mungkin perlu handling khusus
        elif "503" in str(error_str) or "SERVICE_UNAVAILABLE" in str(error_str):
            return {
                "is_quota_error": False,
                "retry_delay": 30,
                "user_message": "Layanan AI sedang tidak tersedia, mencoba lagi...",
                "should_retry": True
            }
        
        elif "500" in str(error_str) or "INTERNAL" in str(error_str):
            return {
                "is_quota_error": False, 
                "retry_delay": 15,
                "user_message": "Error internal server AI, mencoba lagi...",
                "should_retry": True
            }
        
        else:
            return {
                "is_quota_error": False,
                "retry_delay": 10,
                "user_message": f"Error: {str(error_str)[:100]}...",
                "should_retry": False
            }
            
    except Exception:
        return {
            "is_quota_error": False,
            "retry_delay": 10,
            "user_message": f"Error tidak dikenal: {str(error_str)[:100]}...",
            "should_retry": False
        }

def retry_with_delay_and_confirmation(func, *args, max_retries=3, base_delay=10, **kwargs):
    """
    Fungsi untuk retry dengan delay dan konfirmasi user jika masih error.
    Menangani Google API quota errors dengan smart retry.
    
    Args:
        func: Fungsi yang akan dijalankan
        *args: Arguments untuk fungsi
        max_retries: Maksimal jumlah retry (default: 3)
        base_delay: Delay dasar dalam detik (default: 10)
        **kwargs: Keyword arguments untuk fungsi
    
    Returns:
        Result dari fungsi jika berhasil, atau None jika gagal semua
    """
    for attempt in range(max_retries + 1):
        try:
            result = func(*args, **kwargs)
            if attempt > 0:
                console.print(f"[bold green]Berhasil pada percobaan ke-{attempt + 1}![/bold green]")
            return result
            
        except Exception as e:
            error_info = parse_google_api_error(str(e))
            
            # Tampilkan pesan yang user-friendly
            console.print(f"[bold yellow]{error_info['user_message']}[/bold yellow]")
            
            if attempt < max_retries:
                # Gunakan delay dari API error jika tersedia, atau gunakan exponential backoff
                if error_info['is_quota_error']:
                    delay = error_info['retry_delay']
                    console.print(f"[bold cyan]Menunggu {delay} detik sesuai instruksi API...[/bold cyan]")
                else:
                    # Exponential backoff untuk error lainnya
                    delay = base_delay * (2 ** attempt) + random.uniform(0, 5)
                    delay = min(delay, 120)  # Maksimal 2 menit
                    console.print(f"[bold yellow]Menunggu {delay:.1f} detik sebelum mencoba lagi...[/bold yellow]")
                
                # Countdown timer dengan progress
                for i in range(int(delay), 0, -1):
                    minutes, seconds = divmod(i, 60)
                    if minutes > 0:
                        time_str = f"{minutes}m{seconds:02d}s"
                    else:
                        time_str = f"{seconds}s"
                    
                    console.print(f"\r[dim]⏳ Countdown: {time_str} tersisa[/dim]", end="")
                    time.sleep(1)
                console.print("\r" + " " * 30 + "\r", end="")  # Clear countdown
                
                continue
            else:
                # Semua retry gagal
                if error_info['is_quota_error']:
                    console.print(f"\n[bold red]Masih ada limit API setelah {max_retries + 1} percobaan.[/bold red]")
                    console.print(Panel(
                        "Limit penggunaan API Google Gemini masih aktif.\n\n"
                        "Opsi:\n"
                        "1. Ketik 'ya' untuk melanjutkan ke tahap berikutnya\n"
                        "2. Ketik 'tunggu' untuk menunggu lebih lama\n"
                        "3. Ketik 'tidak' untuk berhenti",
                        title="[yellow]Limit API[/yellow]",
                        border_style="yellow"
                    ))
                    
                    user_choice = Prompt.ask("Pilihan", choices=["ya", "tunggu", "tidak"], default="tunggu")
                    
                    if user_choice == "ya":
                        console.print("[bold yellow]Melanjutkan ke tahap berikutnya...[/bold yellow]")
                        return None
                    elif user_choice == "tunggu":
                        extra_wait = 120  # Tunggu 2 menit tambahan
                        console.print(f"[bold cyan]Menunggu {extra_wait} detik tambahan...[/bold cyan]")
                        for i in range(extra_wait, 0, -1):
                            minutes, seconds = divmod(i, 60)
                            time_str = f"{minutes}m{seconds:02d}s"
                            console.print(f"\r[dim]⏳ Extra wait: {time_str} tersisa[/dim]", end="")
                            time.sleep(1)
                        console.print("\r" + " " * 30 + "\r", end="")
                        
                        # Coba sekali lagi setelah extra wait
                        try:
                            result = func(*args, **kwargs)
                            console.print("[bold green]Berhasil setelah extra wait![/bold green]")
                            return result
                        except Exception:
                            console.print("[bold yellow]Masih gagal, melanjutkan ke tahap berikutnya...[/bold yellow]")
                            return None
                    else:
                        console.print("[bold red]Proses dihentikan oleh user.[/bold red]")
                        raise e
                else:
                    # Error non-quota
                    console.print(f"\n[bold red]Semua {max_retries + 1} percobaan gagal![/bold red]")
                    console.print(Panel(
                        f"Error terakhir: {error_info['user_message']}\n\n"
                        "Apakah Anda ingin melanjutkan ke tahap berikutnya?\n"
                        "Ketik 'ya' untuk melanjutkan atau 'tidak' untuk berhenti.",
                        title="[red]Konfirmasi Lanjut[/red]",
                        border_style="red"
                    ))
                    
                    user_choice = Prompt.ask("Lanjutkan", choices=["ya", "tidak"], default="tidak")
                    
                    if user_choice.lower() == "ya":
                        console.print("[bold yellow]Melanjutkan ke tahap berikutnya meskipun ada error...[/bold yellow]")
                        return None
                    else:
                        console.print("[bold red]Proses dihentikan oleh user.[/bold red]")
                        raise e

def setup_model():
    """Memuat environment variables dan menyiapkan model AI."""
    load_dotenv()
    google_api_key = os.getenv("GOOGLE_API_KEY")
    if not google_api_key:
        raise ValueError("GOOGLE_API_KEY tidak ditemukan di environment variables.")
        
    provider = GoogleProvider(api_key=google_api_key)
    model = GoogleModel('gemini-2.5-flash', provider=provider)
    return model

def save_document_file(filename: str, content: str):
    """Menyimpan konten ke file JSON dan mencetak pesan konfirmasi."""
    with open(filename, "w", encoding="utf-8") as f:
        f.write(content)
    console.print(f"\n[bold green]Sukses![/bold green] Dokumen juga disimpan ke file [cyan]{filename}[/cyan]")

def safe_run_agent(agent, prompt, step_name):
    """Wrapper untuk menjalankan agent dengan error handling."""
    try:
        result = agent.run_sync(prompt)
        return result
    except Exception as e:
        console.print(f"[bold red]Error di {step_name}:[/bold red] {str(e)}")
        raise

# ==================================================================================================
# MEMORY MANAGEMENT
# ==================================================================================================

class Memory:
    """Class untuk menyimpan dan mengelola semua dokumen yang dihasilkan selama sesi."""
    def __init__(self):
        self.storage = {}

    def set(self, key: str, value: str):
        """Menyimpan atau memperbarui dokumen di memori."""
        self.storage[key] = value
        console.log(f"Memori diperbarui: Dokumen '[bold cyan]{key}[/bold cyan]' telah disimpan.")

    def get(self, key: str) -> str:
        """Mengambil dokumen dari memori berdasarkan kuncinya."""
        return self.storage.get(key, f"Error: Dokumen dengan nama '{key}' tidak ditemukan.")

    def list_documents(self) -> List[str]:
        """Mengembalikan daftar semua nama dokumen yang tersimpan di memori."""
        return list(self.storage.keys())

# ==================================================================================================
# TOOLS
# ==================================================================================================

def user_input_tool(ctx: RunContext, prompt: str) -> str:
    """Meminta input dari pengguna dengan pesan tertentu."""
    console.print(Panel(f"[bold yellow]{prompt}[/bold yellow]", title="[cyan]Butuh Input Anda[/cyan]", border_style="cyan"))
    response = Prompt.ask(">>> ")
    return response

def create_memory_tools(memory: Memory):
    """Factory untuk membuat tool yang berinteraksi dengan memori."""
    def list_available_documents_tool(ctx: RunContext, prompt: str) -> str:
        """Gunakan tool ini untuk melihat daftar semua dokumen yang tersedia di memori."""
        docs = memory.list_documents()
        console.print(Panel(
            f"Tool: [bold cyan]list_available_documents_tool[/bold cyan]\nAksi: Menampilkan dokumen di memori.\nHasil: {docs}",
            title="[green]Tool Digunakan[/green]", border_style="green"
        ))
        return f"Dokumen yang tersedia adalah: {', '.join(docs)}"

    def read_document_tool(ctx: RunContext, document_name: str) -> str:
        """Gunakan tool ini untuk membaca isi dari dokumen spesifik yang ada di memori. Wajib sertakan nama dokumen yang valid."""
        content = memory.get(document_name)
        console.print(Panel(
            f"Tool: [bold cyan]read_document_tool[/bold cyan]\nAksi: Membaca dokumen '[yellow]{document_name}[/yellow]'.",
            title="[green]Tool Digunakan[/green]", border_style="green"
        ))
        return content

    return [list_available_documents_tool, read_document_tool]

def mermaid_debug_tool(ctx: RunContext, mermaid_code: str) -> str:
    """Tool untuk debug dan validasi kode Mermaid."""
    try:
        # Basic syntax validation
        lines = mermaid_code.strip().split('\n')
        errors = []
        
        # Check for basic Mermaid structure
        if not lines:
            errors.append("Kode Mermaid kosong")
            
        first_line = lines[0].strip() if lines else ""
        valid_diagrams = [
            "flowchart", "graph", "sequenceDiagram", "classDiagram", 
            "stateDiagram", "erDiagram", "pie", "gantt", "gitgraph",
            "architecture", "c4Context", "c4Container", "c4Component"
        ]
        
        if not any(first_line.startswith(diagram) for diagram in valid_diagrams):
            errors.append(f"Diagram type tidak valid. Harus dimulai dengan salah satu: {', '.join(valid_diagrams)}")
        
        # Check for common syntax errors
        bracket_count = mermaid_code.count('[') - mermaid_code.count(']')
        paren_count = mermaid_code.count('(') - mermaid_code.count(')')
        brace_count = mermaid_code.count('{') - mermaid_code.count('}')
        
        if bracket_count != 0:
            errors.append(f"Bracket tidak seimbang: {bracket_count} bracket tidak tertutup")
        if paren_count != 0:
            errors.append(f"Parenthesis tidak seimbang: {paren_count} parenthesis tidak tertutup")
        if brace_count != 0:
            errors.append(f"Brace tidak seimbang: {brace_count} brace tidak tertutup")
        
        # Check for invalid characters in node IDs
        for line in lines[1:]:  # Skip first line (diagram type)
            if '-->' in line or '--->' in line:
                # This is a connection line, check node IDs
                parts = line.split('-->')
                if len(parts) != 2:
                    parts = line.split('--->')
                
                if len(parts) == 2:
                    node1 = parts[0].strip()
                    node2 = parts[1].strip()
                    
                    # Remove labels in brackets
                    node1 = node1.split('[')[0].split('(')[0].strip()
                    node2 = node2.split('[')[0].split('(')[0].strip()
                    
                    # Check for invalid characters
                    invalid_chars = [' ', '-', '+', '=', '!', '@', '#', '$', '%', '^', '&', '*']
                    for char in invalid_chars:
                        if char in node1:
                            errors.append(f"Node ID '{node1}' mengandung karakter tidak valid: '{char}'")
                        if char in node2:
                            errors.append(f"Node ID '{node2}' mengandung karakter tidak valid: '{char}'")
        
        if errors:
            console.print(Panel(
                f"Tool: [bold cyan]mermaid_debug_tool[/bold cyan]\nDitemukan {len(errors)} error:\n" + 
                "\n".join([f"- {error}" for error in errors]),
                title="[red]Mermaid Debug Errors[/red]", border_style="red"
            ))
            return f"Ditemukan {len(errors)} error dalam kode Mermaid:\n" + "\n".join([f"- {error}" for error in errors])
        else:
            console.print(Panel(
                f"Tool: [bold cyan]mermaid_debug_tool[/bold cyan]\nKode Mermaid valid!",
                title="[green]Mermaid Debug Success[/green]", border_style="green"
            ))
            return "Kode Mermaid terlihat valid! Tidak ditemukan error syntax."
            
    except Exception as e:
        error_msg = f"Error saat debug Mermaid: {str(e)}"
        console.print(Panel(
            f"Tool: [bold cyan]mermaid_debug_tool[/bold cyan]\n{error_msg}",
            title="[red]Debug Tool Error[/red]", border_style="red"
        ))
        return error_msg

def create_documentation_tools(memory: Memory):
    """Factory untuk membuat tool khusus dokumentasi."""
    memory_tools = create_memory_tools(memory)
    
    def save_markdown_file_tool(ctx: RunContext, filename: str, content: str) -> str:
        """Tool untuk menyimpan file markdown."""
        try:
            with open(filename, "w", encoding="utf-8") as f:
                f.write(content)
            console.print(Panel(
                f"Tool: [bold cyan]save_markdown_file_tool[/bold cyan]\nFile berhasil disimpan: {filename}",
                title="[green]File Saved[/green]", border_style="green"
            ))
            return f"File markdown berhasil disimpan: {filename}"
        except Exception as e:
            error_msg = f"Error menyimpan file: {str(e)}"
            console.print(Panel(
                f"Tool: [bold cyan]save_markdown_file_tool[/bold cyan]\n{error_msg}",
                title="[red]Save Error[/red]", border_style="red"
            ))
            return error_msg
    
    return memory_tools + [save_markdown_file_tool]
