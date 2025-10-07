# Data Science & Artificial Intelligence

<div align="center">

[![Python Version](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-Educational-green.svg)](LICENSE)
[![NTU](https://img.shields.io/badge/university-NTU-red.svg)](https://www.ntu.edu.sg/)

*Comprehensive coursework and projects for the NTU SCTP Data Science & Artificial Intelligence Program*

</div>

---

## 📋 Table of Contents

- [Overview](#-overview)
- [Modules](#-modules)
- [Repository Structure](#-repository-structure)
- [Environment Setup](#-environment-setup)
- [Author](#-author)

---

## 🎯 Overview

This repository contains assignments, projects, and learning materials from the Nanyang Technological University (NTU) SCTP in Data Science and Artificial Intelligence. The program covers fundamental to advanced topics in data science, machine learning, and AI applications.

---

## 📚 Modules

### Module 1 - Foundations of Data Science: Python and SQL

Foundational concepts in data science including:
- Python programming fundamentals
- Data structures and algorithms
- SQL database querying and management
- Data manipulation with Pandas
- Introduction to data analysis

### Module 2 - Scalable Data Solutions: Big Data Engineering Essentials
**Status:** *Upcoming*

Big data technologies and engineering practices:
- Distributed computing frameworks (Hadoop, Spark)
- Data pipeline design and ETL processes
- Cloud-based data storage solutions
- Data lake and data warehouse architectures
- Stream processing and real-time analytics

### Module 3 - Building Intelligent Systems: Machine Learning and Generative AI
**Status:** *Upcoming*

Machine learning fundamentals and generative AI:
- Supervised and unsupervised learning algorithms
- Model training, evaluation, and optimization
- Introduction to neural networks
- Generative AI models and applications
- Feature engineering and selection

### Module 4 - AWS Certified AI Practitioner
**Status:** *Upcoming*

AWS cloud services and AI/ML deployment:
- AWS AI/ML services (SageMaker, Rekognition, Comprehend)
- Cloud infrastructure for AI workloads
- Model deployment and monitoring
- Cost optimization and scaling strategies
- Preparation for AWS AI Practitioner certification

### Module 5 - Transforming Business with GPT: Hands-on Generative AI Applications
**Status:** *Upcoming*

Practical applications of generative AI:
- Large Language Models (LLMs) and GPT architecture
- Prompt engineering and fine-tuning
- Building AI-powered applications
- Integration with business processes
- Ethical considerations and responsible AI

### Module 6 - Full Stack Programming and Deployment of AI Solutions
**Status:** *Upcoming*

End-to-end AI solution development and deployment:
- Full stack web development (frontend and backend)
- RESTful API design for AI services
- Containerization with Docker and Kubernetes
- CI/CD pipelines for ML/AI projects
- Production monitoring and maintenance

---

## 📁 Repository Structure

```
DSAI-Assignments/
├── README.md                                    # Project documentation
├── environment.yml                              # Conda environment configuration
└── lessons/                                     # Course modules (git submodules)
    └── 5m-data-1.1-intro-data-science/         # Introduction to Data Science
        ├── notebooks/                           # Jupyter notebooks
        ├── assignments/                         # Assignment solutions
        └── projects/                            # Module projects
```

---

## 🛠 Environment Setup

This repository uses Conda for environment management. To set up the development environment:

```bash
# Clone the repository with submodules
git clone --recursive https://github.com/azniosman/DSAI-Assignments.git
cd DSAI-Assignments

# Create conda environment from environment.yml
conda env create -f environment.yml

# Activate the environment
conda activate dsai
```

If you've already cloned the repository without submodules:
```bash
git submodule update --init --recursive
```

---

## 👤 Author

**Muhammad Azni Osman**

- NTU SCTP DSAI Program Student
- GitHub: [@azniosman](https://github.com/azniosman/)

---