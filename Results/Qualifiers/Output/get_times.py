import glob
import json
import csv


with open('results.csv', 'w', newline='', encoding="utf-8") as csvfile:
    fieldnames = ["Folder", "Opponent", "Outcome", "Player", "Max Tick % used", "Game Length"]
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()
    for fp in glob.iglob("*/agent_*.txt"):

        bruh_log_file = fp
        replay_file = fp[:-11] + "replay.json"
        results_file = fp[:-11] + "results.json"
        folder = fp[:-12]


        with open(bruh_log_file) as f:
            lines = f.read().splitlines()
            times = []
            for line in lines:
                if "TIME: " in line:
                    line = line[line.find("TIME: ") : -1]
                    line = float(line[6:])
                    times.append(line)

            time = max(times, default="NA")

        with open(results_file) as f:
            data = json.load(f)
            game_end_reason = data["reason"]
            agent = "a" if data["agent_a"] == "bruh" else "b"
            opponent = data["agent_b"] if agent == "a" else data["agent_a"]
            for num, letter in eval(data["agent_number_mapping"]).items():
                if letter == agent:
                    id = num
            player = "Wizard" if id == "0" else "Knight"
            if data["winning_agent_letter"] is None:
                outcome = "Tie"
            elif data["winning_agent_letter"] == agent:
                outcome = "Win"
                if data["reason"] == "agent crashed":
                    outcome += " (by default)"
            else:
                outcome = "Loss"
        try:
            with open(replay_file) as f:
                data = json.load(f)
                tick = max(data["payload"]["history"], key=lambda x: x["tick"])["tick"]
        except FileNotFoundError:
            tick = "NA"
        writer.writerow({
            "Folder": folder,
            "Opponent": opponent,
            "Outcome": outcome,
            "Player": player,
            "Max Tick % used": time,
            "Game Length": tick
        })
