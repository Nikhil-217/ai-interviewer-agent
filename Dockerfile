# Use official lightweight Python image
FROM python:3.11-slim

# Set working directory inside container
WORKDIR /workspace

# Copy requirements file first to take advantage of Docker cache
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application files
COPY . .

# Expose port 8000
EXPOSE 8000

# Run FastAPI app using uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
