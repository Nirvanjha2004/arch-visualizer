"""
Run this locally to debug what tree-sitter extracts.
Usage: python debug_ast.py
"""
from services.ast_parser import parse_files

# Minimal test cases
test_files = {
    "frontend/src/App.jsx": """
import React, { useState } from 'react'
import AnalyzerForm from './components/AnalyzerForm.jsx'
import LoadingState from './components/LoadingState.jsx'
import DiagramViewer from './components/DiagramViewer.jsx'

export default function App() { return <div /> }
""",
    "frontend/src/components/AnalyzerForm.jsx": """
import React, { useState } from 'react'
export default function AnalyzerForm({ onSubmit }) { return <form /> }
""",
    "backend/main.py": """
from dotenv import load_dotenv
from fastapi import FastAPI
from services.github_service import GitHubService
from services.ast_parser import parse_files
from services.graph_builder import build_graph
from agents.langgraph_agent import run_agent
""",
}

results = parse_files(test_files)
for fm in results:
    print(f"\n{'='*60}")
    print(f"FILE:     {fm.path}")
    print(f"LANGUAGE: {fm.language}")
    print(f"IMPORTS:  {fm.imports}")
    print(f"CLASSES:  {fm.classes}")
    print(f"FUNCS:    {fm.functions}")
