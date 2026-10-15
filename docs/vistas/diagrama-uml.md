# Diagrama UML

Fecha de referencia: 2026-10-14. El diagrama de clases resume las entidades persistidas. No lista columnas de auditoría ni de infraestructura. Los atributos son los que distinguen el modelo.

```mermaid
classDiagram
    class User {
        +email
        +email_confirmed
        +password
    }
    class Profile {
        +display_name
        +role
        +points
    }
    class EditorPreference {
        +locale
        +theme
        +require_semicolons
        +index_base
    }
    class Project {
        +name
        +visibility
        +deleted_at
    }
    class Algorithm {
        +name
        +source
        +language_options
    }
    class AlgorithmVersion {
        +number
        +source
    }
    class Execution {
        +status
        +limits
    }
    class ExecutionEvent {
        +kind
        +text
        +line
    }
    class Community {
        +name
    }
    class Membership
    class LearningPath {
        +name
        +is_published
        +is_bank
    }
    class Challenge {
        +activity_type
        +points
    }
    class ChallengeAttempt {
        +status
        +score
    }
    class Practice {
        +name
        +pseudocode
    }

    User "1" --> "1" Profile
    User "1" --> "1" EditorPreference
    User "1" --> "*" Project
    Project "1" --> "*" Algorithm
    Algorithm "1" --> "*" AlgorithmVersion
    Algorithm "1" --> "*" Execution
    Execution "1" --> "*" ExecutionEvent
    User "1" --> "*" Community
    Community "1" --> "*" Membership
    User "1" --> "*" Membership
    LearningPath "1" --> "*" Challenge
    Challenge "1" --> "*" ChallengeAttempt
    User "1" --> "*" ChallengeAttempt
    User "1" --> "*" Practice
```

Relaciones que el dibujo deja fuera para poder leerse: `Folder`, `ShareLink`, `LanguageProfile`, `PathAssignment`, `Hint`, `Concept` y `AuditEvent`. Están en [modelo-de-datos.md](../modelo-de-datos.md). `EditorPreference.locale` es `es` o `en`.

## Componentes, vista UML

```mermaid
flowchart LR
    subgraph cliente [Cliente]
        Auth
        Workbench
        LearningLab
        Composer
    end
    subgraph servidor [Servidor]
        API
        Core[language_core]
        Runner
    end
    Auth --> API
    Workbench --> API
    LearningLab --> API
    Composer --> Workbench
    API --> Runner
    Runner --> Core
```

`Composer` no llama al núcleo. Entrega texto al banco de trabajo, y a partir de ahí el fuente sigue el camino del editor.

Volver al [índice](indice.md).
