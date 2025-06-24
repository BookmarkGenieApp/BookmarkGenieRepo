import logging
import json
import azure.functions as func


def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("[DependencyVerifier] Checking for numpy and scikit-learn...")

    try:
        import numpy as np
        import sklearn
        result = {
            "numpy_version": np.__version__,
            "sklearn_version": sklearn.__version__,
            "status": "✅ numpy and scikit-learn are available."
        }
        logging.info("[DependencyVerifier] All dependencies present.")
        return func.HttpResponse(
            json.dumps(result, ensure_ascii=False),
            mimetype="application/json",
            status_code=200
        )

    except ImportError as e:
        error_msg = f"❌ Missing module: {str(e)}"
        logging.error(f"[DependencyVerifier] {error_msg}")
        return func.HttpResponse(
            json.dumps({"status": error_msg}),
            mimetype="application/json",
            status_code=500
        )
