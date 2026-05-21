import json
import os

DATA_FILE = os.path.join(os.path.dirname(__file__), "Topic Detection Data.json")

with open(DATA_FILE, "r", encoding="utf-8") as f:
    FUND_DATA = json.load(f)


def _detect_fund(q):
    if "large cap" in q or "largecap" in q:
        return "large_cap"
    if "flexi cap" in q or "flexicap" in q:
        return "flexi_cap"
    if "elss" in q or "tax saver" in q:
        return "elss"
    if "midcap" in q or "mid cap" in q:
        return "midcap"
    return "large_cap"


def detect_topic(question):
    q = question.lower()
    if "what is sip" in q or "what is a sip" in q:
        return ("general", "what_is_sip")
    if "what is expense" in q:
        return ("general", "what_is_expense_ratio")
    if "what is exit" in q:
        return ("general", "what_is_exit_load")
    if "what is nav" in q:
        return ("general", "what_is_nav")
    if "what is elss" in q:
        return ("general", "what_is_elss")
    if "lock-in" in q or "lockin" in q or "lock in" in q:
        return ("general", "elss_lockin")
    if "statement" in q or "download" in q or "capital gains" in q:
        return ("general", "statement_download")
    if "expense ratio" in q:
        return (_detect_fund(q), "expense_ratio")
    if "exit load" in q:
        return (_detect_fund(q), "exit_load")
    if "lump sum" in q:
        return (_detect_fund(q), "lump_sum_minimum")
    if "sip frequency" in q or "frequency" in q:
        return (_detect_fund(q), "sip_frequency")
    if "sip" in q or "minimum sip" in q:
        return (_detect_fund(q), "sip_minimum")
    if "benchmark" in q:
        return (_detect_fund(q), "benchmark")
    if "riskometer" in q or "risk level" in q:
        return (_detect_fund(q), "riskometer")
    if "nav" in q:
        return ("general", "what_is_nav")
    return None


def get_answer(question):
    topic_tuple = detect_topic(question)
    if not topic_tuple:
        return (
            "I could not find data for that query. Please visit the official source.",
            "https://www.miraeassetmf.co.in",
        )
    try:
        fund_key, topic_key = topic_tuple
        entry = FUND_DATA[fund_key][topic_key]
        if entry["answer"] == "[FILL IN]":
            answer = (
                "This data has not been entered yet. "
                "Please check the official Mirae Asset website for accurate information."
            )
            source_url = "https://www.miraeassetmf.co.in"
            return (answer, source_url)
        return (entry["answer"], entry["source_url"])
    except KeyError:
        return (
            "I could not find data for that query. Please visit the official source.",
            "https://www.miraeassetmf.co.in",
        )
