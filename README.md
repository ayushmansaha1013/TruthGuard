2. Create a README.md with this special header at the very top (required by HF Spaces):

YAML

---
title: TruthGuard Backend
emoji: 🛡️
colorFrom: blue
colorTo: green
sdk: docker
pinned: false






# 🛡️ TruthGuard AI

**Deepfake & Misinformation Detection Platform for Civic Education**  
*Aligned with UN SDG 4 (Quality Education) & SDG 16 (Peace, Justice, and Strong Institutions)*

## 🌟 Overview
TruthGuard AI is a privacy-first, multi-modal platform designed to combat the rise of AI-generated deepfakes and misinformation. It provides real-time image scanning via a browser extension, text-based fact-checking via a web portal, and an analytics dashboard for educators to track digital literacy trends.

## 🚀 Key Features
- **🕵️ Privacy-First Browser Extension:** Scans images for deepfakes using Edge AI (TensorFlow.js), ensuring images are processed locally on the user's device with **zero data leakage**.
- **💬 RAG Fact-Checking Portal:** Verifies viral text claims using Retrieval-Augmented Generation (RAG) grounded in real-time, verified news sources to prevent AI hallucinations.
- **📊 Educator Dashboard:** Allows teachers to view analytics on flagged content and auto-generate digital literacy quizzes based on current misinformation trends.
- **🔒 Defense-in-Depth Security:** Implements JWT authentication, RBAC, API rate-limiting, chunked uploads (DoS prevention), and prompt-injection defenses.

## 🏗️ System Architecture
```text
[User/Browser] --> [Edge AI / Extension] (Local Image Processing)
       |
       v
[React Web Portal] --> [FastAPI Gateway (JWT/Rate Limit)] --> [AI Microservices]
       |                                                       ├── CV (HuggingFace)
       |                                                       └── RAG (Groq + Tavily/DDG)
       v
[Supabase DB] <--> [Audit Logs & RBAC]
