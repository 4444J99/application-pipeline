# KRYPTO-VELAMEN: Visual Identity & Diagrams

These five visual designs represent the technical architecture, theoretical framework, and community-driven mission of the KRYPTO-VELAMEN instrument.

---

## 1. The "Double-Channel" Logic (Mermaid)
This diagram illustrates the core compositional engine: how queer subjectivity is split into simultaneous surface and substrate stories.

```mermaid
graph TD
    A[Queer Subjectivity & Desire] --> B{The Encoding Schema}
    
    subgraph "The Double-Channel Text"
    B --> C[SURFACE CHANNEL]
    B --> D[SUBSTRATE CHANNEL]
    
    C --> C1[Public Story / Linguistic Camouflage]
    D --> D1[Interior Truth / Encoded Desire]
    
    C1 -. "Syntactic Alignment" .-> D1
    end
    
    C1 --> E[AUTHENTIC PRESENCE]
    D1 --> E
    
    style C fill:#f9f,stroke:#333,stroke-width:2px
    style D fill:#bbf,stroke:#333,stroke-width:2px
    style E fill:#dfd,stroke:#333,stroke-width:4px
```

---

## 2. The Instrument Interface (ASCII Art)
A mock-up of the "Compositional Dials" used to calibrate the level of concealment vs. visibility in a given text.

```text
========================================================================
| KRYPTO-VELAMEN // INSTRUMENT v1.0 // CALIBRATION INTERFACE           |
========================================================================
|                                                                      |
|  [ CONCEALMENT DIALS ]                                               |
|                                                                      |
|  1. Rimbaud Drift    [||||||||||||||||||..........]  64% (Camouflage)|
|  2. Wilde Mask       [||||||||||||||||||||||||....]  82% (Surface)   |
|  3. Burroughs Control [||||||||||..................]  38% (Structure) |
|                                                                      |
|  ------------------------------------------------------------------  |
|                                                                      |
|  [ VISIBILITY DIALS ]                                                |
|                                                                      |
|  4. Lorde Voice      [||||||||||||||||||||||||||..]  94% (Naming)    |
|  5. Arenas Scream    [||||||||||||||||............]  52% (Excess)    |
|  6. Acker Piracy     [||||||||||||||||||||........]  70% (Inscribe)  |
|                                                                      |
|  ------------------------------------------------------------------  |
|  STATUS: SECURE // IDENTITY: PSEUDO-ALPHA-9 // ARCHIVE: ACTIVE       |
========================================================================
```

---

## 3. Distributed Platform Architecture (Mermaid)
This diagram maps the microservices architecture, emphasizing community safety and risk-calibrated identity.

```mermaid
graph LR
    User([Queer Subject]) --> ID[Identity Node]
    
    subgraph "Security Layer"
    ID --> PM[Pseudonym Manager]
    PM --> RC[Risk Calibration]
    end
    
    subgraph "Collaboration Layer"
    RC --> CN[Community Node]
    CN --> ED[Encrypted DMs]
    CN --> CA[Co-Authoring Engine]
    end
    
    subgraph "Storage Layer"
    CA --> AE[Archive Engine]
    AE --> KG[Knowledge Graph]
    end
    
    KG --> Out[Distributed Survival Folios]
    
    style Security Layer fill:#fff5f5,stroke:#ff0000
    style Collaboration Layer fill:#f5fff5,stroke:#00ff00
    style Storage Layer fill:#f5f5ff,stroke:#0000ff
```

---

## 4. The Compositional Engine (ASCII Diagram)
A visualization of the "machine" logic: where research flows in and survival tools flow out.

```text
      [ 20 AUTHOR STUDIES ]       [ 26 WORLD-BUILDING MODULES ]
               |                                |
               v                                v
    ________________________________________________________
   |                                                        |
   |             KRYPTO-VELAMEN SYNTHESIS CORE              |
   |________________________________________________________|
               |                |               |
               v                v               v
      [ MECHANISM ATLAS ]  [ AUTHOR CROSSWALK ] [ VISIBILITY SCHEMA ]
               |                |               |
               \________________|_______________/
                                |
                                v
                  [ THE DISTRIBUTED INSTRUMENT ]
                                |
                __________________________________
               |                                  |
               v                                  v
      [ COMMUNITY WORKSHOPS ]            [ SURVIVAL FOLIOS ]
```

---

## 5. The Community Knowledge Loop (Mermaid)
Showing how lived experience is transformed into reproducible survival strategies for the NYC community.

```mermaid
sequenceDiagram
    participant C as Community Member
    participant I as Instrument (KRYPTO-VELAMEN)
    participant N as Identity Node
    participant F as Survival Folio
    participant NYC as NYC Community Center

    C->>N: Lived Experience (Input)
    N->>I: Encoding (Double-Channel)
    I->>I: Synthesis (Mechanism Atlas)
    I->>F: Generation (Field Guide)
    F->>NYC: Distribution (Physical/Digital)
    NYC-->>C: Reproducible Strategy
```
