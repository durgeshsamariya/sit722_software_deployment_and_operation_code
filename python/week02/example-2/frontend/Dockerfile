# frontend/Dockerfile
# Uses Nginx to serve the static frontend files.

# Use a lightweight Nginx image
FROM nginx:alpine

# Copy the Nginx default configuration to serve from /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy the frontend application files into the Nginx web root directory
COPY . /usr/share/nginx/html

# Expose port 80, the default HTTP port for Nginx
EXPOSE 80

# Command to run Nginx
CMD ["nginx", "-g", "daemon off;"]
