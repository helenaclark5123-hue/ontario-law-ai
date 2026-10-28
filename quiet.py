"""Hide technical warnings and progress bars from the AI libraries.

Imported first by the other scripts, because these settings only work if
they are set before the libraries load.
"""

import logging
import os
import warnings

warnings.filterwarnings("ignore", message="Cannot enable progress bars")

os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")
os.environ.setdefault("HF_HUB_VERBOSITY", "error")
os.environ.setdefault("TRANSFORMERS_VERBOSITY", "error")
os.environ.setdefault("TQDM_DISABLE", "1")
logging.getLogger("torch.distributed.elastic.multiprocessing.redirects").setLevel(logging.ERROR)
