
# EXAMORA

An AI-powered platform that transforms educational PDFs into customizable, high-quality exams.

The platform helps teachers upload course materials, generate questions automatically, evaluate their quality, and review and edit exams before using them with students.

---

## Project Overview

**EXAMORA is an AI-powered educational platform that uses LLMs, RAG, embeddings, and automated evaluation** to understand PDF content and generate exams based on the teacher's requirements.

### Main Flow

```text
Teacher uploads PDF
        ↓
AI analyzes the content
        ↓
Content retrieval + source references
        ↓
Teacher selects exam settings
        ↓
AI generates questions
        ↓
AI evaluates question quality
        ↓
Teacher reviews & edits
        ↓
Teacher Version / Student Version
```

---

#  Core Features

##  PDF Understanding

* Upload educational PDFs
* Extract text from the document
* Preserve page numbers
* Divide content into searchable chunks
* Retrieve relevant content when generating questions
* Provide source/page references for generated questions

---

##  AI Question Generation

Generate multiple types of questions, including:

* Multiple Choice Questions (MCQ)
* True / False
* Short Answer
* Other question types can be added later

Questions can be generated according to:

* Number of questions
* Question type
* Difficulty
* Exam Blueprint
* Source/Page References

---

##  Smart Exam Generation

Teachers can control the structure of the generated exam.

### Exam Settings

| Setting             | Description                                   |
| ------------------- | --------------------------------------------- |
| Number of Questions | Defines the total number of questions         |
| Question Types      | MCQ, True/False, Short Answer, etc.           |
| Difficulty          | Easy, Medium, Hard                            |
| Exam Blueprint      | Defines the desired distribution of questions |
| Source References   | Keeps track of the PDF pages used             |

---

#  Quality & Validation

The system goes beyond simple question generation by automatically evaluating generated questions.

### AI Quality Score

The quality score considers factors such as:

* Relevance
* Difficulty
* Clarity
* Correctness
* Distractor Quality
* Grounding in the source material

### Additional Quality Features

* Duplicate Question Detection
* Question Validation
* AI Critic
* Smart Regeneration
* Difficulty Adjustment
* Question Type Conversion

### Evaluation Flow

```text
Generated Question
       ↓
Quality Evaluation
       ↓
 ┌───────────────┐
 │   Valid?      │
 └───────┬───────┘
         │
    Yes  │  No
         │
         ↓
     Keep Question
              or
       Smart Regeneration
```

---

#  Exam Editor

Teachers can review and modify the generated exam before using it.

### Supported Editing Operations

* Edit Question
* Edit Answer
* Edit Distractors
* Change Difficulty
* Change Question Type
* Regenerate Question

---

#  Teacher & Student Experience

The platform supports two different versions of the exam.

### Teacher Version

Contains:

* Questions
* Correct Answers
* Source/Page References
* Difficulty
* Quality Score
* Editing Controls

### Student Version

Contains:

* Questions
* Answer Choices
* Student Answer Input

Students do not see teacher-only information such as correct answers or internal quality scores.

---

#  Development Phases

## Phase 1 — AI Core

### Goal

Make the AI understand PDF content and generate questions from it.

### Components

#### Farah — PDF Processing

* PDF upload/processing
* Text extraction
* Page number preservation
* Document chunking

#### Habiba — RAG / Embeddings

* Embedding generation
* Vector storage
* Semantic retrieval
* Relevant context retrieval
* Source/page references

#### Hend — Prompting & Question Generation

* Prompt engineering
* Question generation
* MCQ generation
* True/False generation
* Short Answer generation

#### Nima — AI Evaluation

* Question correctness
* Content relevance
* Question suitability
* Answer validation

---

# Phase 2 — Smart Exam

### Goal

Allow teachers to define the exam structure and let the AI generate the exam accordingly.

### Features

* Number of Questions
* Question Types
* Difficulty
* Exam Blueprint
* Page/Source References

### Team Responsibilities

| Member | Responsibility                     |
| ------ | ---------------------------------- |
| Habiba | Retrieval + Source/Page References |
| Nima   | Question Generation                |
| Farah  | Exam Blueprint                     |
| Hend   | Exam Settings UI                   |

---

# Phase 3 — Quality + Editing

### Goal

Make the system more than a basic question generator.

### Features

* AI Quality Score
* Duplicate Detection
* Question Validation
* Smart Regeneration
* Edit Question
* Change Difficulty
* Change Question Type
* Add Question
* Delete Question
* Reorder Questions

### Team Responsibilities

| Member | Responsibility                      |
| ------ | ----------------------------------- |
| Nima   | Grounding + Correctness             |
| Farah  | AI Critic + Regeneration            |
| Hend   | Quality Score + Duplicate Detection |
| Habiba | Exam Editor UI                      |

---

# Phase 4 — Teacher → Student

### Goal

Build the complete teacher-to-student experience for the generated exam.

### Final System

```text
PDF Upload
    ↓
AI Analysis
    ↓
Teacher Settings
    ↓
Exam Generation
    ↓
Quality Evaluation
    ↓
Review & Edit
    ↓
Teacher Version / Student Version
    ↓
Student Exam Interface
```

During this phase, the whole team contributes to:

* AI Integration
* Backend
* Frontend
* Database
* APIs
* Authentication
* Exam Management
* Student Exam Interface

---

# Suggested System Architecture

```text
                    ┌──────────────────┐
                    │     Teacher      │
                    └────────┬─────────┘
                             │
                             ▼
                    ┌──────────────────┐
                    │   Web Frontend   │
                    └────────┬─────────┘
                             │
                             ▼
                    ┌──────────────────┐
                    │    Backend API   │
                    └────────┬─────────┘
                             │
             ┌───────────────┼────────────────┐
             │               │                │
             ▼               ▼                ▼
      ┌────────────┐  ┌─────────────┐  ┌─────────────┐
      │ PDF Service│  │ AI Service  │  │  Database   │
      └─────┬──────┘  └──────┬──────┘  └─────────────┘
            │                │
            ▼                ▼
      ┌────────────┐  ┌─────────────┐
      │ Text +     │  │ RAG /       │
      │ Page Data  │  │ Embeddings  │
      └────────────┘  └──────┬──────┘
                              │
                              ▼
                       ┌─────────────┐
                       │   Question  │
                       │  Generator  │
                       └──────┬──────┘
                              │
                              ▼
                       ┌─────────────┐
                       │ AI Critic / │
                       │ Evaluation  │
                       └──────┬──────┘
                              │
                              ▼
                       ┌─────────────┐
                       │ Exam Editor │
                       └──────┬──────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │ Teacher / Student│
                    │    Exam View     │
                    └──────────────────┘
```

---

# Key AI Pipeline

```text
PDF
 ↓
Text Extraction
 ↓
Chunking + Page Metadata
 ↓
Embeddings
 ↓
Vector Database
 ↓
RAG Retrieval
 ↓
Prompt Construction
 ↓
Question Generation
 ↓
Question Validation
 ↓
Quality Evaluation
 ↓
Smart Regeneration
 ↓
Final Exam
```

---

# Source Grounding

Every generated question should ideally be connected to the content that supports it.

Example:

```text
Question:
What is the primary function of mitochondria?

Answer:
ATP production through cellular respiration.

Source:
Biology.pdf — Page 12
```

This allows teachers to verify where the question came from and helps reduce unsupported AI-generated content.

---

# Technology Stack

The exact technologies can be selected during implementation, but the system can be organized into:

### Frontend

* Modern web framework
* Responsive UI
* Teacher Dashboard
* Exam Settings
* Exam Editor
* Student Exam Interface

### Backend

* REST API or equivalent
* Authentication
* PDF processing
* Exam generation
* Exam management
* Database integration

### AI Layer

* LLM
* Prompt Engineering
* Embeddings
* RAG
* AI Evaluation
* Duplicate Detection

### Storage

* Relational Database
* Vector Database
* PDF/File Storage

---

# Team

| Member     | Main Responsibilities                                                   |
| ---------- | ----------------------------------------------------------------------- |
| **Farah**  | PDF Processing, Exam Blueprint, AI Critic & Regeneration                |
| **Habiba** | RAG, Embeddings, Retrieval, Source/Page References, Exam Editor         |
| **Hend**   | Prompting, Question Generation, UI, Quality Score & Duplicate Detection |
| **Nima**   | AI Evaluation, Grounding, Correctness, Question Generation              |

> Responsibilities can overlap during Phase 4 as the project becomes a complete full-stack application.

---

# Project Goal

The goal is to build an intelligent exam-generation platform that helps teachers move from:

**Course Material → Structured Exam → Reviewed Questions → Student-Ready Exam**

with minimal manual effort.

Instead of simply generating questions, the system focuses on:

**Understanding → Grounding → Generation → Evaluation → Editing**

---

# Future Work

The following features are planned for future versions of the platform:

###  Online Quiz & Publishing

* Publish Quiz
* Generate Shareable Quiz Links
* Online Quiz Hosting
* Student Quiz Submission
* Automatic Grading

###  Student Analytics

* Student Results
* Performance Analytics
* Student Progress Tracking
* Question-Level Performance Analysis

###  Advanced AI Features

* Adaptive Difficulty
* Personalized Quizzes
* Automatic Answer Explanations
* Intelligent Question Recommendations
* Advanced Question Bank Management

###  Content & Exam Management

* Multiple PDF Support
* PowerPoint/Word Import
* Exam Templates
* Question History and Versioning
* Teacher Collaboration
* Export to PDF/DOCX
* LMS Integration

---

##

