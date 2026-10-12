import urllib.parse

class QRCodeService:
    @staticmethod
    def generate_url(data: str, size: str = "300x300") -> str:
        """QR code yaratish uchun API havolasi"""
        encoded_data = urllib.parse.quote(data.strip())
        return f"https://api.qrserver.com/v1/create-qr-code/?size={size}&data={encoded_data}"
