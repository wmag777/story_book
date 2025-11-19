# Story Visual Generator - Django Web App

A Django web application for generating visual stories using AI. Input your story text, and the app will automatically extract characters and scenes, then generate images for each scene using Google's Gemini (Nano Banana) model.

## Features

- **Project Management**: Create and manage multiple story projects
- **Automatic Story Processing**: Extract characters and scenes from story text using OpenAI
- **Character Extraction**: Automatically identifies main characters with visual descriptions
- **Scene Splitting**: Intelligently splits stories into illustratable scenes
- **Multi-Model Image Generation**: Choose between multiple AI models:
  - Google Nano Banana (Gemini)
  - Stability AI (Stable Diffusion)
  - Seedance (Coming Soon)
- **Multiple Art Styles**: Choose from various art styles (Ghibli, Manga, Pixar, etc.)
- **Story Viewer**: View your complete illustrated story in a beautiful layout

## Prerequisites

- Python 3.8+
- Django 5.0+
- API Keys for:
  - OpenAI (for text processing)
  - Google Gemini (for Google Nano Banana model)
  - Stability AI (optional, for Stable Diffusion)
  - Seedance (optional, coming soon)

## Installation

1. **Clone the repository**
```bash
cd new-story-generator
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Set up environment variables**
Copy the example env file and add your API keys:
```bash
cp .env.example .env
```

Edit `.env` and add your API keys:
```
OPENAI_KEY=your_openai_api_key_here
GOOGLE_API=your_google_gemini_api_key_here
STABILITY_API_KEY=your_stability_api_key_here  # Optional
SEEDANCE_API_KEY=your_seedance_key_here_when_available  # Future
```

4. **Run database migrations**
```bash
python manage.py makemigrations
python manage.py migrate
```

5. **Create a superuser (optional, for admin access)**
```bash
python manage.py createsuperuser
```

6. **Run the development server**
```bash
python manage.py runserver
```

7. **Access the application**
Open your browser and navigate to: `http://127.0.0.1:8000/`

## Usage

1. **Create a New Project**
   - Click "New Project" on the homepage
   - Enter a project name
   - Select an art style
   - Choose an AI model for image generation

2. **Input Your Story**
   - Go to your project and click "Input Story"
   - Paste or type your full story text
   - Click "Extract Scenes & Characters"
   - The AI will automatically extract characters and split the story into scenes

3. **Generate Images**
   - Click on any scene to open the Scene Manager
   - Review and edit the scene prompt if needed
   - Click "Generate Image with [Your Selected Model]"
   - Wait for the image to be generated

4. **View Your Story**
   - Click "View Story" to see all scenes with their generated images
   - The story viewer displays your complete illustrated story

## Project Structure

```
new-story-generator/
├── manage.py             # Django management script
├── requirements.txt      # Python dependencies
├── .env.example         # Environment variables template
├── .gitignore           # Git ignore rules
├── LICENSE              # MIT License
├── README.md            # This file
├── story_django/        # Django project settings
│   ├── settings.py      # Project configuration
│   ├── urls.py          # URL configuration
│   └── wsgi.py          # WSGI application
├── stories/             # Main Django app
│   ├── models.py        # Database models
│   ├── views.py         # View controllers
│   ├── urls.py          # App URL routing
│   ├── admin.py         # Django admin interface
│   ├── services/        # Business logic
│   │   ├── story_processing.py  # AI text processing
│   │   └── image_generation.py  # Image generation
│   ├── templates/       # HTML templates
│   └── migrations/      # Database migrations
├── examples/            # Example scripts
│   └── test_image_generation.py  # Standalone image generation test
├── media/               # User-uploaded and generated files
├── static/              # CSS, JS, and static assets
└── venv/               # Python virtual environment (not in repo)
```

## Available Art Styles

- Ghibli Style
- Line Art Style
- Pixel Art Style
- Water Color Style
- Fairy Tale Style
- Game RPG Style
- Manga Style
- Pixar 3D Style
- Anime Style
- Cinematic Style

## API Services Used

- **OpenAI GPT-4**: For extracting characters and scenes from story text
- **Google Gemini**: Google Nano Banana model for image generation
- **Stability AI**: Stable Diffusion Ultra for high-quality image generation
- **Seedance**: (Coming Soon) Future AI model integration

## Troubleshooting

- **Missing API Keys**: Make sure you've added your API keys to the `.env` file
- **Image Generation Fails**: Check your Google API quota and ensure the Gemini API is enabled
- **Story Processing Fails**: Verify your OpenAI API key is valid and has sufficient credits

## Admin Interface

Access the Django admin interface at `http://127.0.0.1:8000/admin/` to:
- Manage projects, characters, and scenes
- View and edit generated content
- Monitor system data

## Testing & Examples

### Running the Example Script

Test the image generation functionality without the web interface:

```bash
# Basic usage with default watercolor style and Google Nano Banana
python examples/test_image_generation.py

# Use Stability AI model
python examples/test_image_generation.py --model stability_ai

# Specify both style and model
python examples/test_image_generation.py --style pixar-3d --model stability_ai

# Custom output directory
python examples/test_image_generation.py --style manga-style --model google_nano_banana --output my_test_images
```

The example script demonstrates:
- How to use the Django services in standalone scripts
- Character description replacement in prompts
- Image generation with error handling
- Different art style options

## Development

To modify the image generation model or add new features:
- Image generation logic: `stories/services/image_generation.py`
- Story processing logic: `stories/services/story_processing.py`
- Database models: `stories/models.py`
- Views and controllers: `stories/views.py`

## Notes

- Images are stored locally in the `media/generated_images/` directory
- The app uses SQLite database by default (can be changed in settings)
- Character placeholders in scenes use the format `{CharacterName}`

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request. For major changes, please open an issue first to discuss what you would like to change.

## Security

- Never commit your `.env` file or expose API keys
- All API keys should be stored as environment variables
- The `.gitignore` file is configured to exclude sensitive files