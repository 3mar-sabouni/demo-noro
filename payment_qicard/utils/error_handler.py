from odoo import _

class QiCardErrorHandler:
    # Comprehensive error code mapping
    ERROR_CODES = {
        1: "Order Already Exists",
        2: "Order Not Found",
        3: "Order Already Cancelled",
        4: "No Compatible Services Found",
        5: "Cannot Process Request",
        6: "Requisites Not Found",
        7: "Requisites Already Exists",
        8: "Cannot Create New Requisites",
        9: "Terminal Not Found",
        10: "Payment Already Exists",
        11: "Max Number of Payments for Order Exceeded",
        12: "Payment Not Found",
        13: "Unknown Strategy",
        14: "Processing Impossible",
        15: "Cannot Cancel Payment",
        16: "Cannot Confirm Payment",
        17: "Cannot Finish Authentication",
        18: "Refunds Not Allowed",
        19: "Payment Parameters Not Found",
        20: "Refund Error",
        21: "Validation Error",
        22: "Incorrect Payment State",
        23: "Internal System Error",
        24: "External System Error",
        26: "Invalid Payment Form Domain",
        27: "Bad Credentials",
        28: "Limit Violation",
        29: "Transfer Not Found",
        30: "Incorrect Transfer State",
        31: "Token Not Found",
        32: "Token Process Not Allowed",
        33: "Cannot Cancel Transfer",
        34: "Transfer Already Exists",
        35: "Invalid Token Type"
    }

    @classmethod
    def handle_qicard_error(cls, error_response):
        """
        Handle QiCard API error responses
        
        :param error_response: Dictionary containing error information
        :return: Raises appropriate Odoo exception
        """
        if not error_response or 'error' not in error_response:
            return False

        error = error_response['error']
        error_code = error.get('code')
        error_description = error.get('description', '')

        # Specific error handling based on error codes
        if error_code == 21:  # Validation Error
            # Handle currency-specific errors
            if "currency" in error_description.lower():
                return (_(
                    "Currency Error: %s\n"
                    "Please ensure you are using the correct currency for this transaction."
                ) % error_description)
        
        elif error_code == 27:  # Bad Credentials
            return (_(
                "Authentication Failed: Invalid QiCard API credentials. "
                "Please check your terminal ID, and ensure your authentication is configured properly."
            ))
        
        elif error_code == 28:  # Limit Violation
            return (_(
                "Transaction Limit Exceeded: The payment amount may be "
                "outside the allowed transaction limits."
            ))
        
        elif error_code in [23, 24]:  # System Errors
            return (_(
                "System Error: %s\n"
                "Please try again later or contact support."
            ) % cls.ERROR_CODES.get(error_code, "Unknown System Error"))
        
        # Generic error handling for other error codes
        error_message = cls.ERROR_CODES.get(
            error_code, 
            f"Unknown Error (Code {error_code})"
        )
        
        return (_(
            "QiCard Payment Error: %s\n"
            "Description: %s"
        ) % (error_message, error_description))