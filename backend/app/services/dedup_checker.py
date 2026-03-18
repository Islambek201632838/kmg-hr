import numpy as np
from app.services.rag_pipeline import encode_texts


def cosine_similarity(a: list[float], b: list[float]) -> float:
    a, b = np.array(a), np.array(b)
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-9))


async def check_duplicates(
    new_goals: list[str],
    existing_goals: list[str],
    threshold: float = 0.85,
) -> list[dict]:
    """
    Check if new goals are duplicates of existing ones.
    Returns list of {index, is_duplicate, similar_to, similarity}.
    Uses matrix cosine similarity for efficiency.
    """
    if not existing_goals or not new_goals:
        return [{"index": i, "is_duplicate": False} for i in range(len(new_goals))]

    new_vecs = np.array(await encode_texts(new_goals))
    existing_vecs = np.array(await encode_texts(existing_goals))

    # Normalize
    new_norm = new_vecs / (np.linalg.norm(new_vecs, axis=1, keepdims=True) + 1e-9)
    ex_norm = existing_vecs / (np.linalg.norm(existing_vecs, axis=1, keepdims=True) + 1e-9)

    # Cosine similarity matrix: (new x existing)
    sim_matrix = new_norm @ ex_norm.T

    results = []
    for i in range(len(new_goals)):
        max_idx = int(np.argmax(sim_matrix[i]))
        max_sim = float(sim_matrix[i, max_idx])
        results.append({
            "index": i,
            "is_duplicate": max_sim >= threshold,
            "similar_to": existing_goals[max_idx] if max_sim >= threshold else None,
            "similarity": round(max_sim, 3),
        })

    return results
