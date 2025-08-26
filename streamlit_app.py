import os
import time
from typing import Optional

import requests
import streamlit as st


# ---------- Config ----------
DEFAULT_API_BASE = os.getenv("OLMOCR_API_URL", "http://localhost:8000")


def get_api_base() -> str:
    # Allow changing via sidebar and persist in session
    if "api_base" not in st.session_state:
        st.session_state.api_base = DEFAULT_API_BASE
    return st.session_state.api_base.rstrip("/")


def set_api_base(new_base: str):
    st.session_state.api_base = new_base.rstrip("/")


# ---------- API client helpers ----------
def api_create_job(api_base: str, file_bytes: bytes, filename: str, output_format: str = "markdown") -> dict:
    # POST /jobs with multipart file; output_format as query param
    url = f"{api_base}/jobs"
    params = {"output_format": output_format}
    files = {"file": (filename, file_bytes, "application/pdf")}
    resp = requests.post(url, params=params, files=files, timeout=60)
    resp.raise_for_status()
    return resp.json()


def api_get_job(api_base: str, job_id: str) -> dict:
    url = f"{api_base}/jobs/{job_id}"
    resp = requests.get(url, timeout=20)
    resp.raise_for_status()
    return resp.json()


def api_download_result(api_base: str, job_id: str) -> tuple[str, bytes, Optional[str]]:
    # Returns (filename, content_bytes, content_type)
    url = f"{api_base}/jobs/{job_id}/download"
    resp = requests.get(url, timeout=60)
    resp.raise_for_status()
    disposition = resp.headers.get("content-disposition", "")
    filename = "result"
    if "filename=" in disposition:
        # content-disposition: attachment; filename=foo.md
        try:
            filename = disposition.split("filename=", 1)[1].strip().strip('"')
        except Exception:
            pass
    return filename, resp.content, resp.headers.get("content-type")


# ---------- UI ----------
st.set_page_config(page_title="OLMOCR – OCR Web UI", page_icon="📄", layout="wide")

st.title("📄 OLMOCR – OCR Web UI")
st.caption("Upload a PDF, process via the FastAPI backend, and view the resulting Markdown.")

# Sidebar: settings and status
with st.sidebar:
    st.header("Settings")
    api_base_input = st.text_input("API base URL", value=get_api_base(), help="FastAPI base URL (no trailing slash)", key="api_base_input")
    if st.button("Save API URL"):
        set_api_base(api_base_input)
        st.success(f"API set to {get_api_base()}")

    st.divider()
    st.subheader("Active Job")
    if "active_job_id" in st.session_state and st.session_state.active_job_id:
        st.write(f"Job ID: `{st.session_state.active_job_id}`")
        if st.button("Clear job state"):
            for k in [
                "active_job_id",
                "job_status",
                "job_progress",
                "job_filename",
                "job_error",
                "result_markdown",
                "result_filename",
            ]:
                st.session_state.pop(k, None)
            st.experimental_rerun()
    else:
        st.write("No active job")


# Initialize state keys
for key, default in [
    ("active_job_id", None),
    ("job_status", None),
    ("job_progress", 0.0),
    ("job_filename", None),
    ("job_error", None),
    ("result_markdown", None),
    ("result_filename", None),
]:
    if key not in st.session_state:
        st.session_state[key] = default


# Upload and start form
with st.form("upload_form"):
    uploaded = st.file_uploader("Upload a PDF", type=["pdf"], accept_multiple_files=False)
    output_fmt = st.selectbox("Output format", ["markdown", "json"], index=0)
    submitted = st.form_submit_button("Start OCR", type="primary", use_container_width=True)

if submitted:
    if not uploaded:
        st.error("Please select a PDF file first.")
    else:
        try:
            api_base = get_api_base()
            with st.status("Creating OCR job…", expanded=True) as status:
                st.write("Uploading file to API…")
                job = api_create_job(api_base, uploaded.getvalue(), uploaded.name, output_format=output_fmt)
                st.session_state.active_job_id = job.get("job_id")
                st.session_state.job_status = job.get("status")
                st.session_state.job_progress = float(job.get("progress", 0.0))
                st.session_state.job_filename = job.get("filename")
                st.write(f"Job created: {st.session_state.active_job_id}")
                status.update(label="Job created", state="complete")
        except requests.HTTPError as e:
            msg = e.response.text if e.response is not None else str(e)
            st.error(f"API error creating job: {msg}")
        except Exception as e:
            st.error(f"Failed to create job: {e}")


def render_progress(job: dict):
    progress = float(job.get("progress", 0.0))
    status = job.get("status", "queued")
    current_page = job.get("current_page")
    total_pages = job.get("total_pages")

    st.write(f"Status: `{status}`")
    if total_pages:
        st.write(f"Pages: {current_page}/{total_pages}")
    st.progress(min(100, max(0, int(progress))))


def try_fetch_markdown(api_base: str, job_id: str) -> Optional[str]:
    try:
        filename, content, content_type = api_download_result(api_base, job_id)
        st.session_state.result_filename = filename
        # Try decode as text
        text = None
        # Some servers may send 'text/markdown' or 'text/plain; charset=utf-8'
        if content_type and ("markdown" in content_type or "text/" in content_type):
            try:
                text = content.decode("utf-8")
            except Exception:
                try:
                    text = content.decode("latin-1")
                except Exception:
                    text = None
        else:
            # Fallback: try utf-8 anyway
            try:
                text = content.decode("utf-8")
            except Exception:
                text = None
        return text
    except Exception as e:
        st.session_state.job_error = f"Download error: {e}"
        return None


# Polling block
if st.session_state.active_job_id:
    api_base = get_api_base()
    job = None
    try:
        job = api_get_job(api_base, st.session_state.active_job_id)
        st.session_state.job_status = job.get("status")
        st.session_state.job_progress = float(job.get("progress", 0.0))
    except Exception as e:
        st.warning(f"Failed to fetch job status: {e}")

    with st.container(border=True):
        st.subheader("Job progress")
        if job:
            render_progress(job)

        status = (st.session_state.job_status or "").lower()
        if status == "completed":
            st.success("Job completed")
            if st.session_state.result_markdown is None and (job.get("output_format") == "markdown" or job.get("result_path", "").endswith(".md")):
                md_text = try_fetch_markdown(api_base, st.session_state.active_job_id)
                if md_text is not None:
                    st.session_state.result_markdown = md_text
            elif st.session_state.result_markdown is None and job.get("result_path", "").endswith(".jsonl"):
                # For JSONL, show an info and offer download
                st.info("Result is JSONL; click the download button below to fetch the file.")
        elif status == "failed":
            st.error(f"Job failed: {job.get('error_message')}")
        else:
            st.button("Refresh status", key="refresh_status", on_click=lambda: None)

    # Result render/download
    if st.session_state.job_status == "completed":
        with st.container(border=True):
            st.subheader("Result")
            if st.session_state.result_markdown:
                st.markdown(st.session_state.result_markdown)
            else:
                # Show a download button regardless of type
                try:
                    fname, content, ctype = api_download_result(api_base, st.session_state.active_job_id)
                    st.download_button(
                        "Download result",
                        data=content,
                        file_name=fname,
                        mime=ctype or "application/octet-stream",
                        use_container_width=True,
                    )
                    if fname.endswith(".md"):
                        try:
                            st.markdown(content.decode("utf-8"))
                        except Exception:
                            pass
                except Exception as e:
                    st.error(f"Unable to fetch result: {e}")


st.divider()
st.caption("Tip: You can set OLMOCR_API_URL env var to point this UI at a remote API.")
