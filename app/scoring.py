def compute_priority(urgency, rainfall, infra_damage):
    score = urgency * 10
    score += rainfall * 2
    if infra_damage == "yes":
        score += 20
    return score
