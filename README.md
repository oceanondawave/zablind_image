# zablind_image

# Zablind Image

A Flask app to host the offline [BLIP](https://huggingface.co/Salesforce/blip-image-captioning-base) model to handle image description for [Zablind](https://github.com/oceanondawave/zablind).

# Caution

- This app is to build the executable program for Windows. Please run it on the Windows environment.

# How to run

- Clone the repository.
- Install Python `3.10.X` (or `3.11.X` - not tested, might not work), do not install the higher or lower versions. Use `winget` to install:
  ```bash
   winget install --id Python.Python.3.10 -e
  ```
- Create the `.venv` with Python `3.10.X` then activate it:
  ```bash
  py -3.10 -m venv venv
  venv\Scripts\activate
  ```
- Install the dependencies:
  ```bash
  pip install -r requirements.txt
  ```
- Download the `BLIP` model into the directory by running `download_model.py`:
  ```bash
  python download_model.py
  ```
- Now you shoule have the `models` folder in the directory to use it absolutely offline.
- Now you can run the server:
  ```bash
  python server.py
  ```
- The server should run at this endpoint: `http://127.0.0.1:47860/caption`.
- How to test the local API:
  -- Use the `POST` method.
  -- At the Headers, use a key as `X-Auth` with the value (default is `zbimage`).
  -- In the `Body`, if you want to post as an image file, choose the key as `image` and post the selected image file. If you want to post as `JSON`, you should follow the structure below:
  `js
	{ path: <path_to_your_image_on_local_storage> }
	`

# How to build (for Windows)

- Install `pyinstaller`:
  ```bash
  pip install pyinstaller
  ```
- Build the executable file:
  ```bash
  pyinstaller server.py --onefile --windowed --add-data "models;models" --add-data "cache;cache" --add-data "startup.mp3;."
  ```
- The `server.exe` should appear at the `dist` folder of the directory. You can run to test it.
