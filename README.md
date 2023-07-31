### RTSP_Screenshot

RTSP_Screenshot is a Flask-based web application that captures screenshots from RTSP streams. It allows you to add, edit, and view RTSP streams, schedule periodic screenshot captures, and manage user authentication.

#### Features

- Add and manage multiple RTSP streams with custom names, URLs, and capture intervals.
- Schedule periodic screenshot captures from the configured RTSP streams.
- Authenticate users with their username and password.
- View a list of configured RTSP streams and their capture statuses.
- Edit existing stream configurations.
- Capture and view screenshots from individual RTSP streams.
- Support for handling disk space constraints during screenshot captures.

#### Prerequisites

- Python 3.10+
- Required Python packages listed in requirements.txt

#### Installation and Usage

1. Clone the repository:
   
bash
   git clone https://github.com/yourusername/RTSP_Screenshot.git
   

2. Change into the project directory:
   
bash
   cd RTSP_Screenshot
   

3. Install the required Python packages using pip:
   
bash
   pip install -r requirements.txt
   

4. Configure the application by updating the config.py file. Set the RTSP_STREAMS list, SECRET_KEY, FREE_DISK_SPACE_GB and USERS dictionary according to your requirements.

5. Start the application:
   
bash
   python app.py
   

6. Access the application in your browser at http://localhost:5000.

#### Acknowledgments

- The Flask framework and extensions
- PIL (Python Imaging Library) for image processing
- APScheduler for scheduling periodic tasks
- Bootstrap for the user interface

Feel free to customize and enhance this application based on your specific needs!