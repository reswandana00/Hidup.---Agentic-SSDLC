# Cashier App Documentation

This document provides comprehensive information about the Cashier App, including its features, technical specifications, and system design.

## Project Overview

The Cashier App is designed to streamline sales processing, inventory management, and reporting for retail stores. It caters to both cashiers and managers, offering role-based access and a user-friendly interface.

## Key Features

- **Sales Processing**: Efficiently handle customer transactions.
- **Inventory Management**: Track stock levels, add new products, and manage existing inventory.
- **Reporting**: Generate sales reports, inventory reports, and other analytical insights for managers.
- **User Management**: Administer user accounts for cashiers and managers with distinct permissions.
- **Payment Processing**: Integrate various payment methods for seamless transactions.

## System Architecture

### C4 Context Diagram
```mermaid
C4Context
    title System Context for Cashier App

    Person(cashier, "Cashier", "Processes sales transactions")
    Person(manager, "Manager", "Manages inventory, users, and reports")

    System(cashierApp, "Cashier App", "The main cashier application")

    System_Boundary(cashierAppBoundary, "Cashier App System") {
        Container(cashierClient, "Cashier App Client", "Desktop Application", "Used by Cashiers for sales processing")
        Container(managerInterface, "Manager Interface", "Web/Desktop Application", "Used by Managers for management tasks")
        Container(appServer, "Application Server", "Python Flask Application", "Handles business logic and data access")
        Container(mysqlDB, "MySQL Database", "Database", "Stores product, sales, user, and inventory data")
    }

    Rel(cashier, cashierClient, "Uses")
    Rel(manager, managerInterface, "Uses")
    Rel_U(cashierClient, appServer, "Sends requests to")
    Rel_U(managerInterface, appServer, "Sends requests to")
    Rel_U(appServer, mysqlDB, "Reads from and writes to", "SQL/TCP")

    Rel_Neighbor(manager, appServer, "Accesses remotely (if web-based)", "HTTPS/Internet")
```

### Data Flow Diagram
```mermaid
graph TD
    A[User (Cashier/Manager)] --> B(Cashier App Client / Manager Interface)
    B --> C{Application Server}
    C -- Read/Write Data --> D[MySQL Database]
    D -- Query Results --> C
    C -- Processed Data/Responses --> B
    B --> A

    subgraph Security Considerations
        C -- Encrypted in Transit --> D
        D -- Encrypted at Rest --> E[Encrypted Data Storage]
        B -- Encrypted over Internet (for Manager Remote) --> C
    end
```

## Security Considerations

### Authentication and Authorization
- **User Authentication**: Both cashiers and managers will be authenticated using usernames and passwords.
- **Role-Based Authorization**: Access to features will be determined by user roles (Cashier or Manager), ensuring that users only have permissions relevant to their responsibilities.

### Data Protection
- **Encryption in Transit**: Sensitive data, especially during communication between the application server and the MySQL database, will be encrypted using SSL/TLS.
- **Encryption at Rest**: Sensitive data stored in the MySQL database (e.g., transaction details) will be encrypted.

### Network Security
- **Secure Communication**: All communication within the local network (LAN) and over the internet (for remote manager access) will utilize secure protocols (e.g., HTTPS for web interfaces, SSL/TLS for database connections).
- **Untrusted Networks**: The internet is considered an untrusted network. Remote access for managers will be secured via SSL/TLS to protect data in transit.

## Environment Requirements

- **Operating System**: Windows 11
- **Database**: MySQL
