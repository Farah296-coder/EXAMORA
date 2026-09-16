"""
exam_blueprint.py
-----------------

Farah's part of Phase 2.

Flow:
    exam_settings.json
        -> load_exam_settings()
        -> create_exam_blueprint()
        -> validate_exam_blueprint()
        -> save_exam_blueprint()

The blueprint defines:
    - how many questions to generate
    - topic for each question
    - learning objective
    - question type
    - difficulty

The resulting blueprint is saved to:
    output/exam_blueprint.json
"""

import json
import os


# -----------------------------
# 1. Allowed values
# -----------------------------

QUESTION_TYPES = [
    "MCQ",
    "True-False",
    "Short Answer",
]

DIFFICULTY_LEVELS = [
    "Easy",
    "Medium",
    "Hard",
]


# -----------------------------
# 2. Load teacher settings
# -----------------------------

def load_exam_settings(
    path: str = "output/exam_settings.json"
) -> dict:
    """
    Loads the settings created by Hend's exam settings system.
    """

    if not os.path.exists(path):
        raise FileNotFoundError(
            f"Exam settings file not found: {path}"
        )

    with open(path, "r", encoding="utf-8") as f:
        settings = json.load(f)

    return settings


# -----------------------------
# 3. Helper: distribute counts
# -----------------------------

def distribute_count(total: int, number_of_groups: int) -> list:
    """
    Distributes `total` questions as evenly as possible
    across `number_of_groups`.

    Example:
        distribute_count(10, 3)
        -> [4, 3, 3]
    """

    if number_of_groups <= 0:
        return []

    base = total // number_of_groups
    remainder = total % number_of_groups

    counts = []

    for i in range(number_of_groups):
        count = base

        if i < remainder:
            count += 1

        counts.append(count)

    return counts


# -----------------------------
# 4. Create blueprint
# -----------------------------

def create_exam_blueprint(settings: dict) -> dict:
    """
    Converts Hend's exam settings into a structured exam blueprint.

    Each blueprint item specifies:
        - topic
        - learning objective
        - question type
        - difficulty
        - count

    The distribution is balanced as evenly as possible.
    """

    num_questions = settings["num_questions"]
    question_types = settings["question_types"]
    difficulty_levels = settings["difficulty_levels"]
    topics = settings["topics"]

    if not topics:
        raise ValueError("At least one topic is required.")

    if not question_types:
        raise ValueError("At least one question type is required.")

    if not difficulty_levels:
        raise ValueError("At least one difficulty level is required.")

    # --------------------------------
    # Step 1: Distribute questions
    # across topics
    # --------------------------------

    topic_counts = distribute_count(
        num_questions,
        len(topics)
    )

    blueprint = []

    for topic_index, topic_entry in enumerate(topics):

        topic = topic_entry["topic"]

        learning_objectives = topic_entry.get(
            "learning_objectives",
            []
        )

        topic_question_count = topic_counts[topic_index]

        if topic_question_count == 0:
            continue

        # --------------------------------
        # Step 2: Create combinations of
        # question type + difficulty
        # --------------------------------

        combinations = []

        for difficulty in difficulty_levels:
            for question_type in question_types:
                combinations.append(
                    {
                        "question_type": question_type,
                        "difficulty": difficulty,
                    }
                )

        combination_counts = distribute_count(
            topic_question_count,
            len(combinations)
        )

        # --------------------------------
        # Step 3: Build blueprint items
        # --------------------------------

        for combination, count in zip(
            combinations,
            combination_counts
        ):

            if count == 0:
                continue

            # If the teacher provided learning objectives,
            # distribute them across the questions.
            if learning_objectives:

                objective_counts = distribute_count(
                    count,
                    len(learning_objectives)
                )

                for objective, objective_count in zip(
                    learning_objectives,
                    objective_counts
                ):

                    if objective_count == 0:
                        continue

                    blueprint.append(
                        {
                            "topic": topic,
                            "learning_objective": objective,
                            "question_type": combination[
                                "question_type"
                            ],
                            "difficulty": combination[
                                "difficulty"
                            ],
                            "count": objective_count,
                        }
                    )

            else:
                # No specific learning objective was provided.
                blueprint.append(
                    {
                        "topic": topic,
                        "learning_objective": None,
                        "question_type": combination[
                            "question_type"
                        ],
                        "difficulty": combination[
                            "difficulty"
                        ],
                        "count": count,
                    }
                )

    exam_blueprint = {
        "total_questions": num_questions,
        "blueprint": blueprint,
    }

    validate_exam_blueprint(
        exam_blueprint,
        settings
    )

    return exam_blueprint


# -----------------------------
# 5. Validate blueprint
# -----------------------------

def validate_exam_blueprint(
    blueprint: dict,
    settings: dict
):
    """
    Makes sure the generated blueprint is consistent
    with the teacher's requested settings.
    """

    total = sum(
        item["count"]
        for item in blueprint["blueprint"]
    )

    expected = settings["num_questions"]

    if total != expected:
        raise ValueError(
            f"Blueprint contains {total} questions, "
            f"but {expected} were requested."
        )

    allowed_types = set(
        settings["question_types"]
    )

    allowed_difficulties = set(
        settings["difficulty_levels"]
    )

    allowed_topics = {
        topic["topic"]
        for topic in settings["topics"]
    }

    for item in blueprint["blueprint"]:

        if item["topic"] not in allowed_topics:
            raise ValueError(
                f"Invalid topic in blueprint: "
                f"{item['topic']}"
            )

        if item["question_type"] not in allowed_types:
            raise ValueError(
                f"Invalid question type: "
                f"{item['question_type']}"
            )

        if item["difficulty"] not in allowed_difficulties:
            raise ValueError(
                f"Invalid difficulty: "
                f"{item['difficulty']}"
            )

        if item["count"] <= 0:
            raise ValueError(
                "Blueprint count must be greater than zero."
            )

        # Make sure the learning objective belongs
        # to the selected topic.
        if item["learning_objective"] is not None:

            topic_entry = next(
                topic
                for topic in settings["topics"]
                if topic["topic"] == item["topic"]
            )

            if (
                item["learning_objective"]
                not in topic_entry["learning_objectives"]
            ):
                raise ValueError(
                    f"Learning objective "
                    f"'{item['learning_objective']}' "
                    f"does not belong to topic "
                    f"'{item['topic']}'."
                )


# -----------------------------
# 6. Save blueprint
# -----------------------------

def save_exam_blueprint(
    blueprint: dict,
    path: str = "output/exam_blueprint.json"
):
    """
    Saves the final blueprint for the retrieval
    and question-generation pipeline.
    """

    directory = os.path.dirname(path)

    if directory:
        os.makedirs(directory, exist_ok=True)

    with open(
        path,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            blueprint,
            f,
            indent=2,
            ensure_ascii=False
        )

    print(
        f"Saved exam blueprint to {path}"
    )


# -----------------------------
# 7. Convert blueprint into
#    generation requests
# -----------------------------

def build_generation_requests(
    blueprint: dict
) -> list:
    """
    Converts blueprint items into individual question requests.

    Example:
        count = 3

    becomes:

        [
            {...},
            {...},
            {...}
        ]

    Each request can later be passed to
    retrieval + question generation.
    """

    requests = []

    for item in blueprint["blueprint"]:

        for _ in range(item["count"]):

            requests.append(
                {
                    "topic": item["topic"],
                    "learning_objective": item[
                        "learning_objective"
                    ],
                    "question_type": item[
                        "question_type"
                    ],
                    "difficulty": item[
                        "difficulty"
                    ],
                }
            )

    return requests


# -----------------------------
# 8. Full Farah pipeline
# -----------------------------

def build_blueprint_from_file(
    settings_path: str = "output/exam_settings.json",
    blueprint_path: str = "output/exam_blueprint.json",
):
    """
    Full Farah pipeline:

        exam_settings.json
            ↓
        create blueprint
            ↓
        validate
            ↓
        save blueprint
    """

    settings = load_exam_settings(settings_path)

    blueprint = create_exam_blueprint(
        settings
    )

    save_exam_blueprint(
        blueprint,
        blueprint_path
    )

    return blueprint


# -----------------------------
# 9. Manual test
# -----------------------------

if __name__ == "__main__":

    blueprint = build_blueprint_from_file()

    print(
        "\n========== EXAM BLUEPRINT ==========\n"
    )

    print(
        json.dumps(
            blueprint,
            indent=2,
            ensure_ascii=False
        )
    )

    requests = build_generation_requests(
        blueprint
    )

    print(
        "\n========== GENERATION REQUESTS ==========\n"
    )

    print(
        json.dumps(
            requests,
            indent=2,
            ensure_ascii=False
        )
    )