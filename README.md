# 🎓 AlunoSaqua - School Management System

**AlunoSaqua** is a robust school management SaaS platform designed to streamline academic administration, improve communication between schools and families, and provide a secure environment for student reporting.

Built with a **Multi-tenant** architecture, the system allows a single Super Admin to manage multiple educational institutions independently, ensuring total data isolation between them.

---

## 🚀 Key Features

### 🏛️ Super Admin (Matriz)
*   **Global Management**: Create, edit, and delete school units.
*   **Director Oversight**: Register and manage School Directors across different units.
*   **Institution Transfers**: Ability to transfer directors or staff between schools through the management dashboard.

### 🏫 School Administration (Directors)
*   **Academic Control**: Manage students, teachers, parents, and psychopedagogues within their specific unit.
*   **User Management**: Full CRUD operations for all school-related roles.
*   **Data Isolation**: Directors only have access to information belonging to their assigned school.

### 👨‍🏫 Teacher & Staff Area
*   **Grade & Attendance**: Real-time management of student grades and attendance records.
*   **Academic Dashboard**: Overview of student performance filtered by subjects.

### 🎓 Student & Parent Portal
*   **Performance Tracking**: View grades, averages, and attendance status.
*   **Anonymous Reporting**: A dedicated "Denúncia" (Reporting) system for students to report incidents securely to psychopedagogues.
*   **Notifications**: Real-time alerts for academic updates and safety measures.

---

## 🛠️ Tech Stack

*   **Backend**: Python (Flask Framework)
*   **Database**: JSON-based NoSQL Mock Database (optimized for rapid prototyping).
*   **Frontend**: HTML5, CSS3 (Bootstrap 5), FontAwesome.
*   **Security**: Password hashing via `werkzeug.security` and secure session management.
*   **DevOps**: Docker & Git (managed via GitHub Desktop).

---

## ⚙️ Installation & Setup

1.  **Clone the repository**:
    ```bash
    git clone [https://github.com/your-username/AlunoSaqua.git](https://github.com/your-username/AlunoSaqua.git)
    ```
2.  **Navigate to the project folder**:
    ```bash
    cd AlunoSaqua
    ```
3.  **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```
4.  **Run the application**:
    ```bash
    python run.py
    ```
5.  **Access the system**:
    Open your browser at `http://127.0.0.1:5000`

---

## 📝 Credentials for Testing

| Role | Username | Password |
| :--- | :--- | :--- |
| **Super Admin** | `admin` | `admin` |
| **Director** | `diretor_saqua` | `admin` |
| **Student** | `202411251` | `alunos` |

---

## 👨‍💻 Developer

**Rosonatt Ferreira Ramos**  
*Software Engineering Student at Universidade Univassouras*  
*IT Solutions Developer at C3 Engenharia*

---

## ⚖️ License

This project is developed for academic purposes under the guidance of Professors André Saraiva and Gioliano.
