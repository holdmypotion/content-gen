import logging
import google.generativeai as genai
import openai
from jinja2 import Environment, FileSystemLoader
import os
from datetime import datetime
from config import settings
from db import get_db

logger = logging.getLogger(__name__)

# Jinja2 environment for templates
template_dir = os.path.join(os.path.dirname(__file__), '..', 'prompts')
jinja_env = Environment(loader=FileSystemLoader(template_dir))


def load_reference_posts():
    """Load reference posts content from ref.jinja2 file."""
    ref_file = os.path.join(template_dir, 'ref.jinja2')

    try:
        with open(ref_file, 'r') as f:
            content = f.read()
        return content

    except Exception as e:
        logger.warning(f"Failed to load reference posts: {str(e)}")
        return ""


# Initialize Google Generative AI
if settings.GOOGLE_API_KEY:
    genai.configure(api_key=settings.GOOGLE_API_KEY)

# Initialize OpenAI
if settings.OPENAI_API_KEY:
    openai.api_key = settings.OPENAI_API_KEY


def save_to_db(data: dict) -> str:
    """Save data to MongoDB."""
    try:
        db = get_db()
        document_id = db.save_content(data)
        logger.info(f"Data saved to MongoDB with ID: {document_id}")
        return document_id
    except Exception as e:
        logger.error(f"Error saving to MongoDB: {str(e)}")
        raise


def register_tasks(celery_app):
    """Register Celery tasks with the app instance."""

    @celery_app.task(bind=True, name='tasks.generate_idea_gemini')
    def generate_idea_gemini(self, reference_keywords: str, reference_posts: list = None):
        """
        Generate an idea for a post based on reference keywords using Gemini.
        """
        try:
            self.update_state(state='PROGRESS', meta={'current': 'Rendering idea prompt'})

            # Load reference posts from ref.jinja2
            loaded_posts = load_reference_posts()

            template = jinja_env.get_template('idea_template.jinja2')
            prompt = template.render(
                    reference_keywords=reference_keywords,
                    reference_posts=loaded_posts
                    )

            self.update_state(state='PROGRESS', meta={'current': 'Calling Gemini API'})

            model = genai.GenerativeModel(settings.GOOGLE_MODEL)
            response = model.generate_content(prompt)
            idea = response.text

            # Log token usage
            if hasattr(response, 'usage_metadata'):
                logger.info(f"Gemini idea generation - Prompt tokens: {response.usage_metadata.prompt_token_count}, "
                            f"Completion tokens: {response.usage_metadata.candidates_token_count}, "
                            f"Total tokens: {response.usage_metadata.prompt_token_count + response.usage_metadata.candidates_token_count}")

            idea_data = {
                    'timestamp': datetime.now().isoformat(),
                    'type': 'idea',
                    'provider': 'gemini',
                    'reference_keywords': reference_keywords,
                    'reference_posts': reference_posts or [],
                    'idea': idea,
                    'posts': []
                    }
            db_file = save_to_db(idea_data)

            generate_post_gemini.delay(
                    idea=idea,
                    reference_keywords=reference_keywords,
                    reference_posts=reference_posts or [],
                    db_file=db_file
                    )

            return {'status': 'success', 'idea': idea, 'db_file': db_file}

        except Exception as e:
            logger.error(f"Error generating idea with Gemini: {str(e)}")
            return {'status': 'error', 'error': str(e)}

    @celery_app.task(bind=True, name='tasks.generate_post_gemini')
    def generate_post_gemini(self, idea: str, reference_keywords: str, reference_posts: list = None, db_file: str = None):
        """
        Generate a post based on the idea using Gemini.
        """
        try:
            self.update_state(state='PROGRESS', meta={'current': 'Rendering post prompt'})

            # Load reference posts from ref.jinja2
            loaded_posts = load_reference_posts()

            template = jinja_env.get_template('post_template.jinja2')
            prompt = template.render(
                    idea=idea,
                    reference_keywords=reference_keywords,
                    reference_posts=loaded_posts
                    )

            self.update_state(state='PROGRESS', meta={'current': 'Calling Gemini API'})

            model = genai.GenerativeModel(settings.GOOGLE_MODEL)
            response = model.generate_content(prompt)
            post = response.text

            # Log token usage
            if hasattr(response, 'usage_metadata'):
                logger.info(f"Gemini post generation - Prompt tokens: {response.usage_metadata.prompt_token_count}, "
                            f"Completion tokens: {response.usage_metadata.candidates_token_count}, "
                            f"Total tokens: {response.usage_metadata.prompt_token_count + response.usage_metadata.candidates_token_count}")

            logger.info(f"Successfully generated post with Gemini for idea: {idea[:50]}...")

            if db_file:
                try:
                    db = get_db()
                    db.append_post(db_file, post)
                    logger.info(f"Post appended to document {db_file}")
                except Exception as e:
                    logger.warning(f"Could not update document {db_file}: {str(e)}, creating new")
                    post_data = {
                            'timestamp': datetime.now().isoformat(),
                            'type': 'post',
                            'provider': 'gemini',
                            'reference_keywords': reference_keywords,
                            'reference_posts': reference_posts or [],
                            'idea': idea,
                            'posts': [post]
                            }
                    db_file = save_to_db(post_data)
            else:
                post_data = {
                        'timestamp': datetime.now().isoformat(),
                        'type': 'post',
                        'provider': 'gemini',
                        'reference_keywords': reference_keywords,
                        'reference_posts': reference_posts or [],
                        'idea': idea,
                        'posts': [post]
                        }
                db_file = save_to_db(post_data)

            return {'status': 'success', 'post': post, 'db_file': db_file}

        except Exception as e:
            logger.error(f"Error generating post with Gemini: {str(e)}")
            return {'status': 'error', 'error': str(e)}

    @celery_app.task(bind=True, name='tasks.generate_idea_gpt')
    def generate_idea_gpt(self, reference_keywords: str, reference_posts: list = None):
        """
        Generate an idea for a post based on reference keywords using GPT.
        """
        try:
            self.update_state(state='PROGRESS', meta={'current': 'Rendering idea prompt'})

            # Load reference posts from ref.jinja2
            loaded_posts = load_reference_posts()
            template = jinja_env.get_template('idea_template.jinja2')
            prompt = template.render(
                    reference_keywords=reference_keywords,
                    )

            self.update_state(state='PROGRESS', meta={'current': 'Calling OpenAI API'})

            response = openai.chat.completions.create(
                    model=settings.OPENAI_MODEL,
                    messages=[{"role": "user", "content": prompt}]
                    )
            idea = response.choices[0].message.content

            # Log token usage
            if hasattr(response, 'usage'):
                logger.info(f"OpenAI idea generation - Prompt tokens: {response.usage.prompt_tokens}, "
                            f"Completion tokens: {response.usage.completion_tokens}, "
                            f"Total tokens: {response.usage.total_tokens}")

            idea_data = {
                    'timestamp': datetime.now().isoformat(),
                    'type': 'idea',
                    'reference_keywords': reference_keywords,
                    'provider': 'gpt',
                    'reference_posts': reference_posts or [],
                    'idea': idea,
                    'posts': []
                    }
            db_file = save_to_db(idea_data)

            generate_post_gpt.delay(
                    idea=idea,
                    reference_keywords=reference_keywords,
                    reference_posts=reference_posts or [],
                    db_file=db_file
                    )

            return {'status': 'success', 'idea': idea, 'db_file': db_file}

        except Exception as e:
            logger.error(f"Error generating idea with GPT: {str(e)}")
            return {'status': 'error', 'error': str(e)}

    @celery_app.task(bind=True, name='tasks.generate_post_gpt')
    def generate_post_gpt(self, idea: str, reference_keywords: str, reference_posts: list = None, db_file: str = None):
        """
        Generate a post based on the idea using GPT.
        """
        try:
            self.update_state(state='PROGRESS', meta={'current': 'Rendering post prompt'})

            # Load reference posts from ref.jinja2
            loaded_posts = load_reference_posts()
            template = jinja_env.get_template('post_template.jinja2')
            prompt = template.render(
                    idea=idea,
                    reference_keywords=reference_keywords,
                    reference_posts=loaded_posts
                    )

            self.update_state(state='PROGRESS', meta={'current': 'Calling OpenAI API'})

            logger.info(f"Prompt: {prompt}")

            response = openai.chat.completions.create(
                    model=settings.OPENAI_MODEL,
                    messages=[{"role": "user", "content": prompt}]
                    )
            post = response.choices[0].message.content

            # Log token usage
            if hasattr(response, 'usage'):
                logger.info(f"OpenAI post generation - Prompt tokens: {response.usage.prompt_tokens}, "
                            f"Completion tokens: {response.usage.completion_tokens}, "
                            f"Total tokens: {response.usage.total_tokens}")

            logger.info(f"Successfully generated post with GPT for idea: {idea[:50]}...")

            if db_file:
                try:
                    db = get_db()
                    db.append_post(db_file, post)
                    logger.info(f"Post appended to document {db_file}")
                except Exception as e:
                    logger.warning(f"Could not update document {db_file}: {str(e)}, creating new")
                    post_data = {
                            'timestamp': datetime.now().isoformat(),
                            'type': 'post',
                            'provider': 'gpt',
                            'reference_keywords': reference_keywords,
                            'reference_posts': reference_posts or [],
                            'idea': idea,
                            'posts': [post]
                            }
                    db_file = save_to_db(post_data)
            else:
                post_data = {
                        'timestamp': datetime.now().isoformat(),
                        'type': 'post',
                        'provider': 'gpt',
                        'reference_keywords': reference_keywords,
                        'reference_posts': reference_posts or [],
                        'idea': idea,
                        'posts': [post]
                        }
                db_file = save_to_db(post_data)

            return {'status': 'success', 'post': post, 'db_file': db_file}

        except Exception as e:
            logger.error(f"Error generating post with GPT: {str(e)}")
            return {'status': 'error', 'error': str(e)}

    @celery_app.task(bind=True, name='tasks.regenerate_post_gemini')
    def regenerate_post_gemini(self, idea: str, reference_keywords: str = '', reference_posts: list = None, db_file: str = None):
        """
        Regenerate a post based on existing idea using Gemini.
        """
        try:
            self.update_state(state='PROGRESS', meta={'current': 'Rendering post prompt'})

            loaded_posts = load_reference_posts()

            template = jinja_env.get_template('post_template.jinja2')
            prompt = template.render(
                    idea=idea,
                    reference_keywords=reference_keywords,
                    reference_posts=loaded_posts
                    )

            self.update_state(state='PROGRESS', meta={'current': 'Calling Gemini API'})

            model = genai.GenerativeModel(settings.GOOGLE_MODEL)
            response = model.generate_content(prompt)
            post = response.text

            if hasattr(response, 'usage_metadata'):
                logger.info(f"Gemini post regeneration - Prompt tokens: {response.usage_metadata.prompt_token_count}, "
                            f"Completion tokens: {response.usage_metadata.candidates_token_count}")

            logger.info(f"Successfully regenerated post with Gemini for idea: {idea[:50]}...")

            if db_file:
                db = get_db()
                db.append_post(db_file, post)
                logger.info(f"Regenerated post appended to document {db_file}")

            return {'status': 'success', 'post': post, 'db_file': db_file}

        except Exception as e:
            logger.error(f"Error regenerating post with Gemini: {str(e)}")
            return {'status': 'error', 'error': str(e)}

    @celery_app.task(bind=True, name='tasks.regenerate_post_gpt')
    def regenerate_post_gpt(self, idea: str, reference_keywords: str = '', reference_posts: list = None, db_file: str = None):
        """
        Regenerate a post based on existing idea using GPT.
        """
        try:
            self.update_state(state='PROGRESS', meta={'current': 'Rendering post prompt'})

            loaded_posts = load_reference_posts()
            template = jinja_env.get_template('post_template.jinja2')
            prompt = template.render(
                    idea=idea,
                    reference_keywords=reference_keywords,
                    reference_posts=loaded_posts
                    )

            self.update_state(state='PROGRESS', meta={'current': 'Calling OpenAI API'})

            response = openai.chat.completions.create(
                    model=settings.OPENAI_MODEL,
                    messages=[{"role": "user", "content": prompt}]
                    )
            post = response.choices[0].message.content

            if hasattr(response, 'usage'):
                logger.info(f"OpenAI post regeneration - Prompt tokens: {response.usage.prompt_tokens}, "
                            f"Completion tokens: {response.usage.completion_tokens}")

            logger.info(f"Successfully regenerated post with GPT for idea: {idea[:50]}...")

            if db_file:
                db = get_db()
                db.append_post(db_file, post)
                logger.info(f"Regenerated post appended to document {db_file}")

            return {'status': 'success', 'post': post, 'db_file': db_file}

        except Exception as e:
            logger.error(f"Error regenerating post with GPT: {str(e)}")
            return {'status': 'error', 'error': str(e)}
