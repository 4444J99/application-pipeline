---
title: "LingFrame"
category: projects
tags: [ai, ci-cd, formal-systems, generative-art, nlp, python, recursive, symbolic, testing]
identity_positions: [independent-engineer, systems-artist]
tracks: [grant, fellowship]
tier: full
review_status: auto-generated
---

# Project: LingFrame

## One-Line
LingFrame — computational rhetoric platform: hierarchical text atomization, 6 analysis modules, 46-text multilingual ...

## Short (100 words)
LingFrame — computational rhetoric platform: hierarchical text atomization, 6 analysis modules, 46-text multilingual corpus, interactive visualizations. A computational rhetoric platform that decomposes text into hierarchical atomic units, applies six configurable analysis modules across every level of linguistic granularity, and generates interactive visualizations — spanning 46 canonical works in 15+ languages across 12 literary traditions. Part of ORGAN-I (Theoria).

## Full
**Technical Architecture:** ### Directory Structure ``` linguistic-atomization-framework/ ├── framework/ # Core library │ ├── core/ # Atomization engine │ │ ├── atomizer.py # Text → hierarchical atom tree │ │ ├── ontology.py # Data structures (Atom, Corpus, etc.) │ │ ├── naming.py # 5 naming strategies │ │ ├── pipeline.py # Analysis orchestration │ │ ├── language.py # Language detection and configuration │ │ ├── tokenizers.py # Script-aware tokenization │ │ ├── registry.py # Component registry │ │ ├── recursion.py # Iterative analysis capability │ │ └── reproducibility.py # Checksum tracking │ ├── analysis/ # 6 analysis modules │ │ ├── base.py # BaseAnalysisModule interface │ │ ├── evaluation.py # 9-step heuristic evaluation │ │ ├── semantic.py # TF-IDF + entity co-occurrence │ │ ├── temporal.py # Verb tense + temporal markers │ │ ├── sentiment.py # VADER / XLM-RoBERTa │ │ ├── entity.py # spaCy NER + domain patterns │ │ └── translation.py # Alignment + embedding comparison │ ├── visualization/ # 5 visualization adapters │ │ ├── adapters/ # D3.js, Plotly, Chart.js adapters │ │ ├── cross_linking.py # Cross-visualization navigation │ │ └── base.py # BaseVisualizationAdapter interface │ ├── output/ # Report formatters │ │ ├── narrative.py # HTML narrative reports │ │ └── scholarly.py # LaTeX, TEI-XML, CoNLL export │ ├── generation/ # Revision suggestion engine │ ├── domains/ # Domain profiles (military, literary, etc.) │ ├── loaders/ # PDF and document ingestion │ ├── llm/ # Optional LLM integration │ └── schemas/ # Atomization schemas (default, Arabic, Chinese, Japanese) │ ├── app/ # Streamlit web interface │ ├── streamlit_app.py # Main web entry point │ └── components/ # UI components │ ├── corpus_observatory.py # Browse, preview, compare 46 texts │ ├── rhetoric_gym.py # Practice exercises with feedback │ ├── analysis_engine.py # Analysis orchestration │ ├── visualization_bridge.py # Visualization rendering │ ├── upload.py # Document upload handler │ └── results.py # Results display │ ├── cli/ # Command-line interfaces │ ├── main.py # Full CLI (atomize, analyze, visualize, migrate, etc.) │ └── simple.py # Simplified one-command interface │ ├── corpus/ # 46 works, 115 files, 12 traditions │ ├──

## Links
- GitHub: https://github.com/organvm-i-theoria/linguistic-atomization-framework
- Organ: ORGAN-I (Theoria) — Theory
