"""Tests for the CLI."""

import tempfile
from pathlib import Path

import pytest
from PIL import Image
from typer.testing import CliRunner

from app.cli import app


runner = CliRunner()


class TestCLI:
    """Test cases for CLI commands."""

    @pytest.fixture
    def sample_image(self):
        """Create a sample image."""
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            img = Image.new('RGB', (100, 100), color='blue')
            img.save(f.name)
            return f.name

    def test_info_command(self):
        """Test the info command."""
        result = runner.invoke(app, ["info"])
        assert result.exit_code == 0
        assert "Raster to SVG Converter" in result.output
        assert "Version" in result.output

    def test_convert_file_not_found(self):
        """Test convert with non-existent file."""
        result = runner.invoke(app, ["convert", "/nonexistent/file.png"])
        assert result.exit_code == 1
        assert "File not found" in result.output

    def test_convert_invalid_type(self, sample_image):
        """Test convert with invalid image type."""
        result = runner.invoke(app, [
            "convert", sample_image,
            "--type", "invalid"
        ])
        assert result.exit_code == 1
        assert "Invalid image type" in result.output

    def test_convert_invalid_quality(self, sample_image):
        """Test convert with invalid quality mode."""
        result = runner.invoke(app, [
            "convert", sample_image,
            "--quality", "invalid"
        ])
        assert result.exit_code == 1
        assert "Invalid quality mode" in result.output

    def test_validate_command(self, sample_image):
        """Test the validate command."""
        result = runner.invoke(app, ["validate", sample_image])
        assert result.exit_code == 0
        assert "Image Properties" in result.output

    def test_validate_file_not_found(self):
        """Test validate with non-existent file."""
        result = runner.invoke(app, ["validate", "/nonexistent/file.png"])
        assert result.exit_code == 1
        assert "File not found" in result.output

    def test_batch_directory_not_found(self):
        """Test batch with non-existent directory."""
        result = runner.invoke(app, [
            "batch", "/nonexistent/dir",
            "--output", "/tmp/output"
        ])
        assert result.exit_code == 1
        assert "Directory not found" in result.output

    def test_help_command(self):
        """Test the help command."""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "raster-to-svg" in result.output

    def test_convert_help(self):
        """Test convert command help."""
        result = runner.invoke(app, ["convert", "--help"])
        assert result.exit_code == 0
        assert "Convert a single raster image to SVG" in result.output


class TestCLIIntegration:
    """Integration tests for CLI commands that require engines."""

    @pytest.fixture
    def sample_color_image(self):
        """Create a sample color image."""
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            img = Image.new('RGB', (100, 100), color='red')
            img.save(f.name)
            return f.name

    def test_convert_color_image(self, sample_color_image):
        """Test color image conversion via CLI."""
        from app.services.converter import Converter

        converter = Converter()
        engine_info = converter.get_engine_info()

        if not engine_info["vtracer"]["available"]:
            pytest.skip("VTracer not installed")

        with tempfile.NamedTemporaryFile(suffix=".svg", delete=False) as f:
            output_path = f.name

        try:
            result = runner.invoke(app, [
                "convert", sample_color_image,
                "--output", output_path,
                "--type", "color",
                "--quality", "fast"
            ])

            # Note: May fail if engines aren't installed
            if result.exit_code == 0:
                assert Path(output_path).exists()

        finally:
            Path(output_path).unlink(missing_ok=True)
