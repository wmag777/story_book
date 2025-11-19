from .image_generation import ImageGenerator


class CharacterGenerator(ImageGenerator):
    """
    Specialized generator for creating character images with consistency features.
    """

    def generate_character(self, prompt, character_name, project_style=None,
                         project_color_scheme=None, project=None, character=None):
        """
        Generate a character image with consistent style.

        Args:
            prompt: Character description prompt
            character_name: Name of the character for file naming
            project_style: Optional style override from project
            project_color_scheme: Optional color scheme from project

        Returns:
            ContentFile with generated character image
        """
        # Enhance prompt with character-specific instructions
        enhanced_prompt = self._enhance_character_prompt(
            prompt,
            project_style,
            project_color_scheme
        )

        # Generate filename base
        filename_base = f"character_{character_name.lower().replace(' ', '_')}"

        # Generate the character image
        return self.generate(enhanced_prompt, filename_base, project=project, character=character)

    def _enhance_character_prompt(self, prompt, style=None, color_scheme=None):
        """
        Enhance the character prompt with style and consistency instructions.
        """
        # Base character generation instructions
        enhanced = f"Character portrait: {prompt}"

        # Add consistency instructions
        enhanced += " Full body character design, clear facial features, consistent proportions."

        # Add style using template if available
        if style and color_scheme:
            # Try to get the style suffix from the prompt template
            from stories.models import PromptTemplate
            try:
                style_template = PromptTemplate.objects.get(
                    template_type='image_style_suffix',
                    is_active=True
                )
                style_suffix = style_template.render(
                    style=style,
                    color_scheme=color_scheme
                )
                enhanced += style_suffix
            except PromptTemplate.DoesNotExist:
                # Only use hardcoded as absolute last resort
                print("WARNING: image_style_suffix template not found, using fallback")
                enhanced += f" Draw in {style} with {color_scheme} colors"
            except ValueError as e:
                print(f"ERROR rendering style template: {e}")
                enhanced += f" Draw in {style} with {color_scheme} colors"
        elif style:
            # If only style is provided without color_scheme
            enhanced += f" Draw in {style} with vibrant colors"
        elif color_scheme:
            # If only color_scheme is provided without style
            enhanced += f" with {color_scheme} colors"

        # Add quality instructions
        enhanced += ". High quality, detailed, professional character design."

        return enhanced

    def generate_with_reference(self, prompt, character_name, reference_image_path):
        """
        Generate a character variation using a reference image for consistency.

        Args:
            prompt: New scene or pose description
            character_name: Name of the character
            reference_image_path: Path to reference image

        Returns:
            ContentFile with generated image
        """
        # This method would integrate with image-to-image generation
        # For now, we'll use standard generation with enhanced prompt
        enhanced_prompt = f"{prompt}. Character should match the appearance and style of the reference character."

        filename_base = f"character_{character_name.lower().replace(' ', '_')}_variant"

        return self.generate(enhanced_prompt, filename_base)

    def create_character_reference_sheet(self, character, poses=None):
        """
        Create a reference sheet with multiple poses/expressions of a character.

        Args:
            character: Character model instance
            poses: List of pose descriptions (default: standard poses)

        Returns:
            List of generated images for the reference sheet
        """
        if poses is None:
            poses = [
                "front view, neutral expression",
                "side profile view",
                "three-quarter view, smiling",
                "action pose",
            ]

        generated_images = []
        base_description = character.description

        for pose in poses:
            prompt = f"{base_description}, {pose}"

            # Generate each pose
            try:
                image = self.generate_character(
                    prompt,
                    f"{character.name}_{pose.replace(' ', '_').replace(',', '')}"
                )
                generated_images.append(image)
            except Exception as e:
                print(f"Error generating pose '{pose}': {str(e)}")
                continue

        return generated_images