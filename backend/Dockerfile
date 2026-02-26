# Use official Python image
FROM python:3.10

# Set working directory
WORKDIR /app

# Copy dependency file first
COPY dependencies.txt .

# Install dependencies (this will install gunicorn too)
RUN pip install --no-cache-dir -r dependencies.txt

# Copy all project files
COPY . .

# Expose Django port
EXPOSE 8000

# Start app using Gunicorn
CMD ["gunicorn", "backend.wsgi:application", "--bind", "0.0.0.0:8000"]
