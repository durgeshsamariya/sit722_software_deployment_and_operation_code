# week03/example-1/frontend/Dockerfile
# Builds a Docker image to serve the static frontend application using Nginx.

# Use a lightweight Nginx image as the base
FROM nginx:alpine

# Copy the custom Nginx configuration file into the container.
# This configures Nginx to serve your HTML/JS/CSS files.
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy all frontend application files (index.html, main.js, etc.)
# into the Nginx default web root directory inside the container.
COPY . /usr/share/nginx/html

# Expose port 80, which is the default HTTP port Nginx listens on.
# This port will be mapped to a host port (e.g., 3000) by Docker Compose.
EXPOSE 80

# Command to run Nginx in the foreground.
# 'daemon off;' ensures Nginx stays in the foreground so Docker can monitor it.
CMD ["nginx", "-g", "daemon off;"]
