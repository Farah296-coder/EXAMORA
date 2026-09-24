import json
import os


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SETTINGS_PATH = os.path.join(BASE_DIR, "output", "exam_settings.json")


def load_exam_settings(path=SETTINGS_PATH):
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def build_blueprint(settings):
    num_questions = settings["num_questions"]
    question_types = settings["question_types"]
    difficulty_levels = settings["difficulty_levels"]
    topics = settings["topics"]

    if not topics:
        raise ValueError("At least one topic is required.")

    blueprint = []

    for i in range(num_questions):
        topic = topics[i % len(topics)]
        question_type = question_types[i % len(question_types)]
        difficulty = difficulty_levels[i % len(difficulty_levels)]

        blueprint.append(
            {
                "topic": topic["topic"],
                "question_type": question_type,
                "difficulty": difficulty,
                "count": 1,
            }
        )

    return {
        "total_questions": num_questions,
        "blueprint": blueprint,
    }


def build_blueprint_from_file(path=SETTINGS_PATH):
    settings = load_exam_settings(path)
    return build_blueprint(settings)


def build_generation_requests(blueprint):
    requests = []

    for item in blueprint["blueprint"]:
        for _ in range(item["count"]):
            requests.append(
                {
                    "topic": item["topic"],
                    "question_type": item["question_type"],
                    "difficulty": item["difficulty"],
                }
            )

    return requests


def validate_exam_blueprint(blueprint):
    if "blueprint" not in blueprint:
        raise ValueError("Blueprint is missing 'blueprint'.")

    for item in blueprint["blueprint"]:
        required = ["topic", "question_type", "difficulty", "count"]

        for field in required:
            if field not in item:
                raise ValueError(
                    f"Blueprint item is missing '{field}'."
                )

    return True


if __name__ == "__main__":
    blueprint = build_blueprint_from_file()

    print(json.dumps(blueprint, indent=4, ensure_ascii=False))

    validate_exam_blueprint(blueprint)

    requests = build_generation_requests(blueprint)

    print("\nGeneration requests:")
    print(json.dumps(requests, indent=4, ensure_ascii=False))