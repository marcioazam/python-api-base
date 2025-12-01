# C4 Context Diagram

## System Context

```mermaid
C4Context
    title System Context Diagram - My App

    Person(user, "User", "Application user")
    Person(admin, "Admin", "System administrator")
    
    System(myapp, "My App", "Main application system")
    
    System_Ext(email, "Email Service", "Sends notifications")
    System_Ext(payment, "Payment Provider", "Processes payments")
    System_Ext(storage, "Cloud Storage", "S3-compatible storage")
    
    Rel(user, myapp, "Uses", "HTTPS")
    Rel(admin, myapp, "Manages", "HTTPS")
    Rel(myapp, email, "Sends emails", "SMTP/API")
    Rel(myapp, payment, "Processes payments", "HTTPS")
    Rel(myapp, storage, "Stores files", "HTTPS")
```

## Description

The My App system provides a REST API for users and administrators. It integrates with external services for email notifications, payment processing, and file storage.
