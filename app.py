# Legacy Streamlit UI — not used by FundBot (index.html + server.py).
# Run: streamlit run app.py  — separate from the Netlify/Railway deployment.

import streamlit as st
from topic_detection import get_answer

EXAMPLE_QUESTIONS = [
    "What is the expense ratio of Mirae Asset Large Cap Fund?",
    "How long is the ELSS lock-in period for Mirae Asset ELSS Tax Saver Fund?",
    "What is the minimum SIP amount for Mirae Asset Flexi Cap Fund?",
    "Does Mirae Asset Midcap Fund have an exit load?"
]





def main() -> None:
    st.set_page_config(
        page_title="Mirae Asset RAG FAQ Assistant",
        page_icon="💼",
        layout="centered"
    )

    st.title("Mirae Asset Mutual Fund FAQ Assistant")
    st.markdown(
        "This app answers factual questions about Mirae Asset mutual funds using scraped official fund pages and OpenAI. "
        "It does not provide investment advice, and responses are based only on retrieved documents."
    )





    st.subheader("Example questions")
    cols = st.columns(2)
    for index, sample in enumerate(EXAMPLE_QUESTIONS):
        if cols[index % 2].button(sample):
            st.session_state["question"] = sample

    question = st.text_input("Ask a question about Mirae Asset funds", value=st.session_state.get("question", ""))

    if st.button("Get Answer") and question.strip():
        with st.spinner("Retrieving the best answer from the knowledge base..."):
            try:
                answer, source_url = get_answer(question.strip())
                st.markdown(f"**Answer:** {answer}")
                st.markdown(f"**Source:** [{source_url}]({source_url})")
            except Exception as exc:
                st.error(f"Unable to retrieve an answer: {exc}")

    st.markdown(
        "---\n"
        "**Disclaimer:** This assistant is informational only. It is not a financial advisor and does not provide investment advice. "
        "Do not use the answer as a substitute for professional guidance."
    )


if __name__ == "__main__":
    main()
