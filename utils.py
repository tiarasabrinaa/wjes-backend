# utils.py
import json
from typing import Dict, Any, Union
from pathlib import Path
import os

def json_parse(json_str: str) -> Union[Dict[str, Any], str]:
    if isinstance(json_str, dict):
        return json_str
    if not isinstance(json_str, str):
        return str(json_str)
    json_str = json_str.strip()
    if json_str.startswith("```json"):
        json_str = json_str[7:].strip()
    if json_str.startswith("```"):
        json_str = json_str[3:].strip()
    if json_str.endswith("```"):
        json_str = json_str[:-3].strip()
    start = json_str.find("{")
    end = json_str.rfind("}") + 1
    if start == -1 or end <= start:
        return json_str
    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        return json_str

def check_files_in_directory(list_ok, directory):
    filename_mapping = {
        "BA Test Commissioning": "Berita Acara Commissioning Test BACT Document Content.txt",
        "BA Test Commisioning": "Berita Acara Commissioning Test BACT Document Content.txt",
        "Laporan 100% Waspang": "Laporan Pekerjaan Selesai 100.txt",
        "BoQ hasil opname": "Lampiran Berita Acara Commissioning Test Bill of Quantity BoQ.txt",
        "Hasil ukur OTDR": "Hasil Ukur OTDR.txt",
        "Hasil ukur Power Meter": "Evidence Pengukuran OPM.txt"
    }
    directory = os.path.abspath(directory)
    result = []
    for item in list_ok:
        expected_file = filename_mapping.get(item)
        if expected_file is None:
            result.append({"item": item, "exists": False, "note": "No mapping defined"})
            continue
        full_path = os.path.join(directory, expected_file)
        found = os.path.isfile(full_path)
        result.append({"item": item, "exists": found})
    return result