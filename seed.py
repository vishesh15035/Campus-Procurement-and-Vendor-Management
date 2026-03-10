from app import app, bootstrap_data


def seed():
    with app.app_context():
        bootstrap_data()
        print("Database seeded successfully!")


if __name__ == "__main__":
    seed()
