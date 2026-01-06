FROM node:18-alpine

WORKDIR /app

# Copy package files first for better caching
COPY package.json package-lock.json* ./

# Install dependencies
RUN npm install

# Copy all source files
COPY . .

# Expose the port
EXPOSE 3000

# Run the development server with explicit host binding
CMD ["npm", "run", "dev"]
