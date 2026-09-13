import os
import requests
import streamlit as st
import dotenv

dotenv_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.env"))
dotenv.load_dotenv(dotenv_path)

API_URL = os.getenv("API_URL")

st.set_page_config(page_title="DarkRag", page_icon="🌌")
st.title("🌌 DarkRag")
st.caption("Ask questions about dark matter based on the indexed scientific articles.")

if "messages" not in st.session_state:
    st.session_state.messages = []


def ask_api(question: str):
    try:
        response = requests.post(
            f"{API_URL}/ask",
            json={"query": question},
            timeout=60,
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.ConnectionError:
        return {
            "answer": None,
            "status": "error",
            "error": (
                f"Could not connect to the API at {API_URL}. "
                "Is it running? (uvicorn src.backend.api:app --reload)"
            ),
        }
    except requests.exceptions.Timeout:
        return {
            "answer": None,
            "status": "error",
            "error": "The API took too long to respond. Please try again.",
        }
    except requests.exceptions.HTTPError as e:
        return {
            "answer": None,
            "status": "error",
            "error": f"API error: {e.response.status_code} — {e.response.text}",
        }


for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("suspicious_citations"):
            with st.expander("⚠ Possible unverified citations"):
                for c in msg["suspicious_citations"]:
                    st.write(f"- ({c})")

question = st.chat_input("Type your question about dark matter...")

if question:
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        with st.spinner("Searching and generating answer..."):
            result = ask_api(question)

        if result["status"] == "error":
            text = f"❌ {result['error']}"
            st.error(text)
            suspicions = []
        else:
            text = result["answer"]
            suspicions = result.get("suspicious_citations", [])
            st.markdown(text)

            if suspicions:
                with st.expander("⚠ Possible unverified citations"):
                    for c in suspicions:
                        st.write(f"- ({c})")

    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": text,
            "suspicious_citations": suspicions,
        }
    )

with st.sidebar:
    st.markdown("### About")
    st.write(
        "DarkRag answers questions based on scientific articles about "
        "dark matter, citing title, authors, year, and page of the sources."
    )
    if st.button("🗑 Clear conversation"):
        st.session_state.messages = []
        st.rerun()
