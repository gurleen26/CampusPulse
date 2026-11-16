"""
Builds a labelled campus-complaint dataset (data/raw/complaints.csv).

The data is SYNTHETIC: complaints are composed from hand-written problem
descriptions, sentence frames, scopes and durations. Urgency follows written
labelling rules (see URGENCY RULES below), so the labels are consistent.

URGENCY RULES
  1. Every problem has a base urgency (0=Low, 1=Medium, 2=High).
  2. Safety / health hazards (fire risk, sewage, intruders, stuck lift ...) are always High.
  3. If the problem affects "everyone / the whole building / all rooms", urgency goes up one level.
  4. If the problem has lasted "more than a week", urgency goes up one level.

Run:  python data/generate_dataset.py [number_of_rows] [seed]
"""
import csv
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT_FILE = ROOT / "raw" / "complaints.csv"
LEVELS = ["Low", "Medium", "High"]

ALL = ["Central Library", "Hostel Block A", "Hostel Block B", "Hostel Block C", "Cafeteria",
       "Computer Lab", "Academic Block 1", "Academic Block 2", "Admin Block", "Auditorium",
       "Sports Complex", "Main Gate", "Parking Area"]
HOSTELS = ["Hostel Block A", "Hostel Block B", "Hostel Block C"]
ACADEMIC = ["Academic Block 1", "Academic Block 2", "Computer Lab", "Auditorium"]

# problem = (phrasings, base_urgency, is_safety_hazard)
CATEGORIES = {
    "Network": (
        ["Central Library", "Computer Lab", "Hostel Block A", "Hostel Block B", "Hostel Block C",
         "Academic Block 1", "Academic Block 2", "Admin Block", "Cafeteria"],
        [
            (["the Wi-Fi is not working", "Wi-Fi connection is not available", "wifi has stopped working"], 1, False),
            (["the internet is very slow", "internet speed is extremely slow", "web pages take forever to load"], 0, False),
            (["unable to connect to the Wi-Fi network", "my device cannot connect to the campus wifi",
              "the Wi-Fi shows connected but there is no internet"], 1, False),
            (["the Wi-Fi keeps disconnecting every few minutes", "wifi signal drops again and again"], 0, False),
            (["LAN ports are not working", "the ethernet sockets are dead", "wired internet ports have no connection"], 1, False),
            (["the router is blinking red and the internet is down", "the access point is switched off"], 1, False),
            (["the login page for campus internet does not load", "the Wi-Fi login portal gives an error"], 1, False),
            (["the internet is down during the online test", "no internet during the scheduled online exam"], 2, False),
            (["the student portal website is not opening", "the college server is not reachable"], 1, False),
            (["no network signal is available", "there is no network coverage at all"], 1, False),
        ],
    ),
    "Electricity": (
        ALL,
        [
            (["there is no electricity", "the power supply is cut", "there is a power outage"], 1, False),
            (["the tube light is flickering", "the light keeps flickering and hurts the eyes", "the lights flicker continuously"], 0, False),
            (["the ceiling fan is not working", "fans are not running", "the fan has stopped rotating"], 0, False),
            (["the light bulb has fused", "the lamp is not glowing", "bulbs are fused and the area is dark"], 0, False),
            (["the power sockets are not working", "charging points give no power", "electric plug points are dead"], 1, False),
            (["sparks are coming out of the switch board", "the switchboard is sparking", "I saw sparks from the socket"], 2, True),
            (["there is a burning smell from the wiring", "a short circuit happened and smoke came from the wire"], 2, True),
            (["live wires are hanging open", "electric wires are exposed and dangerous"], 2, True),
            (["the AC is not cooling", "the air conditioner has stopped working"], 0, False),
            (["voltage keeps fluctuating and damaging devices", "there is frequent voltage fluctuation"], 1, False),
            (["the street lights are not working", "the outdoor lamps are off in the evening"], 1, False),
            (["the generator backup did not start during the power cut", "the inverter backup failed"], 1, False),
        ],
    ),
    "Water Supply": (
        ["Hostel Block A", "Hostel Block B", "Hostel Block C", "Cafeteria", "Academic Block 1",
         "Academic Block 2", "Admin Block", "Sports Complex"],
        [
            (["there is no water supply", "water is not coming in the taps", "the taps are dry"], 1, False),
            (["the water is dirty and muddy", "muddy water is coming from the tap", "the tap water looks yellow"], 1, False),
            (["the water cooler is not working", "drinking water cooler gives warm water", "the water dispenser is out of order"], 0, False),
            (["a tap is leaking continuously", "the tap keeps dripping", "the washroom tap is leaking"], 0, False),
            (["the water pressure is very low", "water comes very slowly from the tap", "weak water flow on the upper floors"], 0, False),
            (["the drinking water smells bad and students fell sick", "contaminated drinking water has made people ill"], 2, True),
            (["a pipe has burst and water is flooding the corridor", "a water pipeline burst and the floor is flooded"], 2, True),
            (["the overhead tank is overflowing", "water is overflowing from the tank", "the water tank keeps overflowing and wasting water"], 1, False),
            (["the RO purifier is not working", "the water purifier has stopped"], 1, False),
            (["there is no hot water", "the geyser gives only cold water"], 0, False),
        ],
    ),
    "Classroom Equipment": (
        ACADEMIC,
        [
            (["the projector is not working", "the projector does not turn on", "projector shows no display"], 1, False),
            (["the projector image is blurry", "the projected display is dim and unreadable"], 0, False),
            (["the microphone is not working", "the mic gives no sound", "the sound system is not working"], 0, False),
            (["there are no markers for the whiteboard", "whiteboard markers are finished", "the duster and markers are missing"], 0, False),
            (["the smart board is not responding", "the interactive board does not respond to touch"], 1, False),
            (["the benches are broken", "a few desks are damaged", "the chair has a broken leg"], 0, False),
            (["the speakers have no sound", "the classroom speaker is not producing audio"], 0, False),
            (["the computers are not booting", "lab computers are not starting", "the desktops show a black screen"], 1, False),
            (["the classroom door lock is broken", "the door of the classroom cannot be locked"], 0, False),
            (["a ceiling fan is loose and wobbling dangerously", "the ceiling fan may fall as it is hanging loose"], 2, True),
            (["the teacher's podium computer is not turning on", "the laptop at the podium does not start"], 1, False),
            (["the HDMI cable is missing", "no cable is available to connect the laptop to the projector"], 0, False),
        ],
    ),
    "Hostel Maintenance": (
        HOSTELS,
        [
            (["my room door lock is broken", "the room lock is jammed", "the door cannot be locked properly"], 1, False),
            (["the cot is broken", "the bed frame is damaged", "my bed is broken and uncomfortable"], 0, False),
            (["the mess food is stale", "the quality of mess food is poor", "the food served in the mess is bad"], 0, False),
            (["many students got food poisoning after dinner in the mess", "students fell ill after eating at the mess"], 2, True),
            (["the washing machine is not working", "the laundry machine is out of order"], 0, False),
            (["the geyser is not heating", "the bathroom geyser is not working"], 0, False),
            (["the window glass is broken", "the window pane is cracked", "the window does not close"], 0, False),
            (["the bathroom drain is blocked", "water is not draining from the bathroom", "the washbasin is clogged"], 1, False),
            (["the lift is stuck between floors", "students are trapped in the lift"], 2, True),
            (["the roof leaks when it rains", "water seeps through the ceiling", "the ceiling is leaking in the room"], 1, False),
            (["the cupboard lock is broken", "my almirah cannot be locked"], 0, False),
            (["the room needs repainting and has damp walls", "walls have damp patches and peeling paint"], 0, False),
        ],
    ),
    "Cleanliness": (
        ALL,
        [
            (["the dustbins are overflowing", "garbage bins are full and not emptied", "a dustbin is full"], 0, False),
            (["the washrooms are very dirty", "toilets are not cleaned", "the restroom is filthy"], 0, False),
            (["garbage has not been collected for days", "waste is piled up and not removed"], 0, False),
            (["there is a bad smell from the drain", "the drain stinks badly"], 0, False),
            (["the floors are not cleaned", "the floor is dusty and unmopped", "the corridor has not been swept"], 0, False),
            (["I saw cockroaches", "rats are running around", "there are many insects and pests"], 1, False),
            (["stagnant water is breeding mosquitoes", "water is stagnating and mosquitoes are increasing"], 1, False),
            (["sewage is overflowing", "the sewer line is overflowing onto the road", "dirty sewage water is flooding the area"], 2, True),
            (["oil is spilled and the floor is slippery", "the floor is wet and slippery after spillage"], 0, False),
            (["the tables are not wiped", "the tables and benches are sticky and dirty"], 0, False),
            (["a dead animal is lying and smelling", "there is a dead rat that has not been removed"], 1, False),
        ],
    ),
    "Security": (
        ["Main Gate", "Parking Area", "Hostel Block A", "Hostel Block B", "Hostel Block C",
         "Central Library", "Sports Complex", "Academic Block 1", "Academic Block 2"],
        [
            (["stray dogs are roaming aggressively", "aggressive stray dogs are scaring students"], 1, False),
            (["unknown people are entering without permission", "an outsider entered the building and nobody stopped him"], 2, True),
            (["the CCTV camera is not working", "surveillance cameras are switched off", "the camera is damaged"], 1, False),
            (["the guard is not checking ID cards", "no security check is happening at the entry"], 1, False),
            (["the street light is off which makes the road unsafe at night", "it is very dark and unsafe at night"], 1, False),
            (["my bike was stolen", "a bicycle was stolen from here", "my helmet and bag were stolen"], 1, False),
            (["my laptop was stolen", "a phone was stolen from the bench"], 1, False),
            (["a student is being harassed by a group", "ragging is happening", "a junior student is being threatened"], 2, True),
            (["a fight is going on between students", "students are fighting and someone is hurt"], 2, True),
            (["a man is stalking girls", "someone is teasing and following girl students"], 2, True),
            (["vehicles are blocking the emergency exit", "the fire exit is blocked by parked vehicles"], 1, False),
            (["the emergency exit door is locked", "the fire exit is chained shut"], 2, True),
        ],
    ),
    "Other": (
        ALL,
        [
            (["the library closes earlier than the displayed timing", "the reading room is locked during working hours"], 0, False),
            (["the timetable shown on the portal is wrong", "the class schedule on the website is not updated"], 0, False),
            (["the fee payment page shows an error", "online fee payment is failing", "money was deducted but the receipt was not generated"], 1, False),
            (["the college bus is coming late", "the bus does not arrive on time", "the bus route timing is not followed"], 0, False),
            (["my ID card has not been issued", "the student ID card is still pending"], 0, False),
            (["the canteen is overcharging", "prices at the canteen are higher than the menu"], 0, False),
            (["sports equipment is not available", "there are no balls or rackets to borrow"], 0, False),
            (["the notice board is not updated", "important notices are not displayed"], 0, False),
            (["attendance is not updated on the portal", "my attendance shows wrongly on the portal"], 0, False),
            (["parking space is not enough", "there is no space to park two wheelers"], 0, False),
            (["a wheelchair ramp is needed", "there is no ramp for students with disabilities"], 1, False),
            (["the exam seating list is not displayed", "the hall ticket is not available for download"], 1, False),
        ],
    ),
}

WIDESPREAD = [", affecting the entire building", ", for all students", ", in all the rooms", ", across the whole block",
              ", everyone is affected", " throughout the building", ", nobody can use it"]
LOCAL = ["", "", "", "", ", only in one room", ", only for me", ", only on one floor", ", affecting a few students",
         ", only near the entrance"]
NEUTRAL_TIME = ["", "", "", " since morning", " since yesterday", " for the last two days", " since last night",
                " for a few hours", " since this afternoon", " today"]
LONG_TIME = [" for more than a week", " for over a week now", " for the past 10 days"]

FRAMES = [
    "{Issue} at {loc}{scope}{time}.",
    "{Issue} in {loc}{scope}{time}, please look into it.",
    "Please fix this: {issue} near {loc}{scope}.",
    "Complaint: {issue} at {loc}{time}{scope}.",
    "Since {since}, {issue} at {loc}{scope}.",
    "Hello, I want to report that {issue} in {loc}{scope}{time}.",
    "{loc}: {Issue}{scope}{time}.",
    "Kindly resolve this issue. {Issue} at {loc}{scope}.",
    "Sir/Madam, {issue} at {loc}{scope}{time}. Request urgent attention.",
    "{Issue}{scope}, location: {loc}{time}.",
]
SINCE = ["morning", "yesterday", "last night", "this afternoon", "two days", "the weekend"]


def add_typo(text, rng):
    """Introduce one small typing mistake to imitate real student writing."""
    words = text.split()
    idx = [i for i, w in enumerate(words) if len(w) > 5 and w.isalpha()]
    if not idx:
        return text
    i = rng.choice(idx)
    w = words[i]
    p = rng.randrange(1, len(w) - 1)
    mode = rng.choice(["swap", "drop"])
    words[i] = (w[:p] + w[p + 1] + w[p] + w[p + 2:]) if mode == "swap" and p + 1 < len(w) else w[:p] + w[p + 1:]
    return " ".join(words)


def make_row(rng, category):
    locations, problems = CATEGORIES[category]
    phrasings, base, safety = rng.choice(problems)
    issue = rng.choice(phrasings)
    loc = rng.choice(locations)

    r = rng.random()
    widespread = r < 0.25
    long_time = rng.random() < 0.12
    scope = rng.choice(WIDESPREAD if widespread else LOCAL)
    time = rng.choice(LONG_TIME if long_time else NEUTRAL_TIME)

    level = base
    if safety:
        level = 2
    else:
        if widespread:
            level += 1
        if long_time:
            level += 1
        level = min(level, 2)

    frame = rng.choice(FRAMES)
    text = frame.format(issue=issue, Issue=issue[0].upper() + issue[1:], loc=loc, scope=scope,
                        time=time, since=rng.choice(SINCE))
    if "{" in text:
        text = text.replace("{", "").replace("}", "")
    text = text.replace(" ,", ",").replace("  ", " ")
    if rng.random() < 0.10:
        text = add_typo(text, rng)
    if rng.random() < 0.08:
        text = text.lower()
    return text, category, LEVELS[level], loc


def generate(n=1800, seed=42, out_file=OUT_FILE):
    rng = random.Random(seed)
    cats = list(CATEGORIES)
    # roughly balanced, "Other" slightly smaller
    weights = [1.0 if c != "Other" else 0.8 for c in cats]
    rows, seen = [], set()
    attempts = 0
    while len(rows) < n and attempts < n * 20:
        attempts += 1
        cat = rng.choices(cats, weights)[0]
        text, cat, urg, loc = make_row(rng, cat)
        key = text.lower()
        if key in seen:      # no exact duplicates
            continue
        seen.add(key)
        rows.append((text, cat, urg, loc))
    out_file = Path(out_file)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["complaint_id", "complaint_text", "category", "urgency", "location"])
        for i, (text, cat, urg, loc) in enumerate(rows, start=1):
            w.writerow([f"D{i:04d}", text, cat, urg, loc])
    return rows


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 1800
    seed = int(sys.argv[2]) if len(sys.argv) > 2 else 42
    rows = generate(n, seed)
    print(f"Wrote {len(rows)} rows to {OUT_FILE}")
