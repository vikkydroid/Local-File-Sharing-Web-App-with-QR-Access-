📁 File Sharing App with QR Code Access & Directory Browser 

A lightweight, Python-based file sharing and directory browsing web app that allows users to access files over the local network via a browser or QR code.  

🔧 Features: 
🌐 Local Network File Sharing over HTTP (http.server based)  
📱 Auto-generated QR Code for easy access on mobile devices  
📂 Dynamic Directory Browser with tile/detail views  
🔍 File & Folder Listing with size, type, and navigation  
🧠 Jinja2 Templating for clean, customizable UI  
🔐 Secure Path Handling to prevent directory traversal 
🤝 Cross-Platform Integration with .NET, Power Automate, etc. ready  
🧾 Supports Static Assets (CSS, JS, SVG) for full front-end flexibility  
☁️ Designed to work with cloud, on-prem, or hybrid setups  

📦 Tech Stack: 
Python 3  
Jinja2  
PyQRCode  
HTTP Server / SocketServer  

💡 Use Cases: Quickly share files from one machine to another over the LAN  
Use QR code to open shared directory directly on a mobile browser  
Browse and download folders/files from a shared directory securely  

🚀 Getting Started: Clone the repo  Place your files in the root directory (FILE_ROOT_DIR)  Run python main.py  Scan the QR or open the IP:Port in browser (e.g. http://192.168.x.x:8010/qr)
