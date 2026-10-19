import os
import tempfile

# Point storage at a scratch dir and pin a secret before app.config is imported.
_TMP = tempfile.mkdtemp(prefix="kb-test-")
os.environ.setdefault("QDRANT_PATH", os.path.join(_TMP, "qdrant"))
os.environ.setdefault("SESSION_SECRET", "test-secret-do-not-use")
os.environ.setdefault("GEMINI_API_KEY", "")
os.environ.setdefault("GROQ_API_KEY", "")
