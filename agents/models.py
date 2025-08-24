"""
Simplified models for SSDLC agents.
Contains streamlined Pydantic models for professional use.
"""
from typing import List, Optional
from pydantic import BaseModel, Field, computed_field

# ==================================================================================================
# SIMPLIFIED MODEL DEFINITIONS
# ==================================================================================================

# --- Core Interview Results ---
class InterviewResults(BaseModel):
    projectName: str = Field(..., description="Nama proyek")
    businessNeeds: str = Field(..., description="Kebutuhan bisnis utama")
    targetUsers: List[str] = Field(..., description="Target pengguna")
    keyFeatures: List[str] = Field(..., description="Fitur utama yang dibutuhkan")
    technicalSpecs: List[str] = Field(..., description="Spesifikasi teknis")

# --- Environment Requirements ---
class EnvironmentRequirements(BaseModel):
    projectName: str
    operatingSystem: List[str] = Field(..., description="OS yang didukung")
    dependencies: List[str] = Field(..., description="Dependensi software")
    networkRequirements: List[str] = Field(..., description="Kebutuhan jaringan")
    securityBaseline: List[str] = Field(..., description="Baseline keamanan")

# --- Security Requirements ---
class SecurityRequirements(BaseModel):
    projectName: str
    userRoles: List[str] = Field(..., description="Peran pengguna")
    threatActors: List[str] = Field(..., description="Aktor ancaman")
    securityControls: List[str] = Field(..., description="Kontrol keamanan")
    dataProtection: List[str] = Field(..., description="Perlindungan data")

# --- Misuse Cases ---
class MisuseCase(BaseModel):
    id: str
    name: str
    actor: str
    description: str
    impact: str
    mitigation: List[str]

class MisuseCases(BaseModel):
    projectName: str
    cases: List[MisuseCase]

# --- System Design ---
class SystemDesign(BaseModel):
    projectName: str
    components: List[str] = Field(..., description="Komponen sistem")
    dataFlow: List[str] = Field(..., description="Alur data")
    interfaces: List[str] = Field(..., description="Interface eksternal")
    trustBoundaries: List[str] = Field(..., description="Batas kepercayaan")

# --- Architecture ---
class SystemArchitecture(BaseModel):
    projectName: str
    architecture: str = Field(..., description="Deskripsi arsitektur")
    components: List[str] = Field(..., description="Komponen utama")
    securityZones: List[str] = Field(..., description="Zone keamanan")
    attackSurfaces: List[str] = Field(..., description="Permukaan serangan")

# --- Threat Analysis ---
class ThreatRisk(BaseModel):
    damage: int = Field(..., ge=0, le=10)
    reproducibility: int = Field(..., ge=0, le=10)
    exploitability: int = Field(..., ge=0, le=10)
    affectedUsers: int = Field(..., ge=0, le=10)
    discoverability: int = Field(..., ge=0, le=10)

    @computed_field
    @property
    def riskScore(self) -> float:
        return (self.damage + self.reproducibility + self.exploitability + 
                self.affectedUsers + self.discoverability) / 5

    @computed_field
    @property
    def riskLevel(self) -> str:
        if self.riskScore >= 8: return "Critical"
        elif self.riskScore >= 6: return "High"
        elif self.riskScore >= 4: return "Medium"
        else: return "Low"

class Threat(BaseModel):
    id: str
    name: str
    description: str
    targetAsset: str
    risk: ThreatRisk
    mitigations: List[str]

class ThreatModel(BaseModel):
    projectName: str
    threats: List[Threat]

# --- File Actions for Generators ---
class FileAction(BaseModel):
    action: str = Field(..., description="Action: create, read, edit, delete")
    file_path: str = Field(..., description="Path to file")
    content: str = Field(None, description="File content for create/edit")
    pattern: str = Field(None, description="Pattern for edit operations")
