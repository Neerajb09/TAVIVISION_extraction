# Use Miniconda as the base image
FROM continuumio/miniconda3

# Set working directory inside the container
WORKDIR /cardiovision/phase1


# Copy requirement files explicitly from the correct location
COPY requirement/conda-requirements.txt .
COPY requirement/pip-requirements.txt .

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Configure Conda to use conda-forge as the default channel
RUN conda config --add channels conda-forge && \
    conda config --set channel_priority flexible

# Create Conda environment using conda-requirements.txt
RUN conda env create --name neeraj --file conda-requirements.txt

# Install Pip dependencies inside Conda
RUN conda run -n neeraj pip install --no-cache-dir -r pip-requirements.txt

COPY requirement/requirement.txt .
RUN conda run -n neeraj pip install -r requirement.txt gunicorn




# Copy application files
COPY . .

# # Make the serve script executable
# RUN chmod +x /cardiovision/phase1/serve
# Move `serve` to a globally accessible location and make it executable
RUN cp /cardiovision/phase1/serve /usr/local/bin/serve && chmod +x /usr/local/bin/serve

# Create a volume for storing files
VOLUME ["/cardiovision/data"]

# Ensure Conda environment is activated by default
SHELL ["conda", "run", "-n", "neeraj", "/bin/bash", "-c"]

# Expose the required port
EXPOSE 8183

# Default command when the container starts
# CMD ["/cardiovision/phase1/serve"]
CMD ["bash", "/usr/local/bin/serve"]













