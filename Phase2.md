## 🧠 Phase 2 — Smart Exam

### Goal

The goal of Phase 2 is to allow teachers to define the structure and requirements of an exam, while the AI automatically builds the exam based on the uploaded course material.

The teacher will be able to specify:

* Number of Questions
* Question Types
* Difficulty Level
* Learning Objectives
* Topics
* Exam Blueprint

Generated questions will also include references to the relevant source pages from the uploaded material.

### Team Responsibilities

**Habiba — Retrieval & Source/Page References**

* Retrieve the most relevant content from the vector database based on the topic and learning objective.
* Retrieve multiple relevant chunks when needed instead of relying on a single result.
* Combine the retrieved chunks into useful context for question generation.
* Preserve the page information associated with each retrieved chunk.
* Provide source/page references for the content used to generate each question.

**Nima — Question Generation**

* Generate questions using the context provided by the retrieval system.
* Follow the requirements defined in the exam blueprint.
* Support the required question types, such as MCQ, True/False, and Short Answer.
* Generate questions according to the requested difficulty level.
* Produce the required number of questions.

**Farah — Exam Blueprint & Learning Objectives**

* Build the exam blueprint based on the teacher's selected settings.
* Define how questions are distributed across topics.
* Associate questions with the appropriate learning objectives.
* Define the required question type and difficulty for each part of the exam.
* Pass the structured blueprint to the retrieval and question-generation pipeline.

**Hend — Exam Settings UI**

* Build the interface that allows the teacher to configure the exam.
* Allow the teacher to select the number of questions.
* Allow selection of question types and difficulty levels.
* Allow selection of topics and learning objectives.
* Pass the selected settings to the exam blueprint system.

### Phase 2 Workflow

Teacher Settings
→ Exam Blueprint & Learning Objectives
→ Relevant Content Retrieval
→ Source/Page References
→ Question Generation
→ AI Evaluation
→ Final Exam
