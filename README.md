# Secure Weather App

[![Live Demo](https://img.shields.io/badge/Live-Demo-blue?style=for-the-badge&logo=streamlit)](https://example.com)

A secure, production-ready weather dashboard built with Streamlit, deployed on AWS EC2 behind Nginx and managed with Terraform.

## 🚀 Live Demo

Live demo: [https://example.com](https://example.com)

> Replace the demo URL above with your actual deployed endpoint once available.

## ✨ Features

- Real-time weather dashboard with city search and location-based forecasts
- Secure login flow for authenticated access
- Rate limiting and input sanitization to prevent abuse
- OpenWeatherMap API key stored securely in AWS Secrets Manager
- AWS deployment using ALB and Nginx reverse proxy
- Separate Security Monitor dashboard for application health and defense metrics
- Infrastructure as Code powered by Terraform

## 🏗️ Architecture

The system is built for secure, scalable weather delivery:

1. **User Interface**: Streamlit app running on AWS EC2
2. **Reverse Proxy**: Nginx handles SSL termination, routing, and request filtering
3. **Load Balancer**: AWS ALB distributes traffic across instances
4. **Secrets Management**: AWS Secrets Manager stores the OpenWeatherMap API key
5. **Monitoring**: Security Monitor dashboard tracks attacks, auth attempts, and rate limits

## 🧰 Tech Stack

- Python + Streamlit
- Nginx reverse proxy
- AWS EC2
- AWS Application Load Balancer (ALB)
- AWS Secrets Manager
- OpenWeatherMap API
- Terraform for provisioning

## 🛠️ Local Setup

1. Clone the repository
   ```bash
   git clone https://github.com/<your-user>/secure-weather-app.git
   cd secure-weather-app
   ```
2. Create a Python virtual environment
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```
3. Install dependencies
   ```bash
   pip install -r requirements.txt
   ```
4. Configure local environment variables
   ```bash
   export OPENWEATHER_API_KEY="your_api_key"
   export STREAMLIT_SECRET_KEY="your_secret_key"
   ```
5. Run the app
   ```bash
   streamlit run main.py
   ```

## ☁️ AWS Deployment

The deployment is managed with Terraform and runs behind AWS infrastructure.

1. Update the Terraform variables in `terraform/variables.tf`
2. Provide AWS credentials with the AWS CLI or environment variables
3. Initialize Terraform
   ```bash
   cd terraform
   terraform init
   ```
4. Review the deployment plan
   ```bash
   terraform plan
   ```
5. Apply infrastructure changes
   ```bash
   terraform apply
   ```
6. Provision EC2 and ALB resources, then deploy Nginx and the Streamlit app

## 🔒 Security Features

- Secure login gate for authenticated access
- API keys never stored in source code
- AWS Secrets Manager holds the OpenWeatherMap API key
- Input validation and sanitization for all user-provided data
- Rate limiting to protect from abusive requests
- Nginx provides reverse proxy controls and request filtering
- Separate Security Monitor dashboard for observability

## �️ Security & Threat Model

### Authentication
- Enforces user authentication before accessing the weather dashboard.
- Uses secure session management and protects endpoints with a login layer.
- Unauthorized users are blocked from sensitive app routes.

### Secrets Management
- Stores the OpenWeatherMap API key in AWS Secrets Manager, not in source code.
- EC2 retrieves secrets at runtime using an IAM role with least privilege.
- Secrets are rotated and managed independently of deployments.

### Rate Limiting
- Applies per-user request limits to reduce abuse and denial-of-service risk.
- Protects the Streamlit endpoints from brute force and high-frequency attacks.
- Uses Nginx and app-level controls to enforce throttling.

### Input Validation
- Sanitizes city and search parameters before use.
- Validates user input against expected patterns and types.
- Rejects malformed or dangerous payloads early in the request pipeline.

### Network Security
- AWS ALB handles HTTPS termination and secures inbound traffic.
- EC2 runs in a public subnet with tight security group rules.
- Security groups restrict inbound access to ALB and allow only necessary ports.
- Nginx provides an additional application-layer boundary.

### Logging & Monitoring
- Security Monitor dashboard tracks authentication, rate limit events, and suspicious requests.
- Logs capture request flow through Nginx and app activity for post-incident analysis.
- Alerts can be added later to notify operators of unusual patterns.

### Potential Risks & Mitigations
- Risk: exposed API key or credential leakage.
  - Mitigation: store secrets in AWS Secrets Manager and avoid hard-coded keys.
- Risk: unauthorized access to dashboards.
  - Mitigation: enforce authentication and restrict app routes.
- Risk: high traffic or brute force attacks.
  - Mitigation: apply rate limiting and Nginx request controls.
- Risk: injection or malformed input.
  - Mitigation: validate and sanitize all user-provided data.

## �🖼️ Screenshots

> Add project screenshots here once available.

- Screenshot 1: Weather Dashboard
- Screenshot 2: Login screen
- Screenshot 3: Security Monitor

## 🌱 Future Improvements

- Add multi-region deployment for higher availability
- Implement OAuth or SSO authentication
- Add caching for faster API responses
- Include automated tests for security flows
- Add CI/CD pipeline for Terraform and Streamlit deployments
- Support additional weather providers and historical data
