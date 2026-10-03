<!-- Gegenereerd door `archi render` — niet handmatig bewerken -->

# Van dienst tot platform

```mermaid
flowchart TD
  accTitle: Van dienst tot platform
  n1["Aanvrager"]
  n2["Vergunning aanvragen"]
  n3["Aanvraag behandelen"]
  n4["Regels toetsen"]
  n5["Zaaksysteem"]
  n6["Regelservice"]
  n7["Overheidscloud"]
  n2 -->|"bedient"| n1
  n3 -.->|"realiseert"| n2
  n4 -->|"ondersteunt"| n3
  n5 -->|"ondersteunt"| n3
  n5 -->|"stuurt aanvraag"| n6
  n6 -.->|"realiseert"| n4
  n7 -->|"host"| n5
  n7 -->|"host"| n6
  classDef application fill:#B4E2FA,stroke:#4A9CC9,color:#0D3D57
  class n4,n5,n6 application
  classDef business fill:#FFF580,stroke:#D4B830,color:#5C4A00
  class n1,n2,n3 business
  classDef technology fill:#C9E7B7,stroke:#7BAF5E,color:#2E4A1E
  class n7 technology
```

*Gegenereerd uit `vergunningverlening.archimate` — pijlstijlen: `--o` bevat (aggregatie/compositie), `-.->` gestippeld (beïnvloedt/realiseert), `-->` overig.*
