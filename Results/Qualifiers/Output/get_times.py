import glob
import json

for fp in glob.iglob("*/agent_*.txt"):
    with open(fp) as f:
        lines = f.read().splitlines()
    times = []
    for line in lines:
        if "TIME: " in line:
            line = line[line.find("TIME: ") : -1]
            line = float(line[6:])
            times.append(line)
    try:
        with open(fp[:-11] + "replay.json") as f:
            data = json.load(f)
            winner = data["payload"]["winning_agent_number"]
        tick = max(data["payload"]["history"], key=lambda x: x["tick"])["tick"]
    except FileNotFoundError:
        winner = "Unknown"
        tick = "NA"
    if "agent_a" in fp:
        player = "Wizard"
    else:
        player = "Knight"
    if (winner == 0 and player == "Wizard") or (winner == 1 and player == "Knight"):
        winner = "Win"
    elif (winner == 1 and player == "Wizard") or (winner == 0 and player == "Knight"):
        winner = "Loss"
    elif winner == "Unknown":
        winner = "Win by Default"
    else:
        winner = "Draw"
    time = max(times, default="NA")
    id = fp[:-12]
    print(id, winner, player, time, tick)
