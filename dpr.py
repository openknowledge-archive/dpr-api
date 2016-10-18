from os.path import join, dirname
from dotenv import load_dotenv
from app import create_app

dot_env_path = join(dirname(__file__), '.env')
load_dotenv(dot_env_path)

application = create_app()

if __name__ == "__main__":
    application.run(debug=True)
