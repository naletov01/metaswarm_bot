

Base = declarative_base()
SessionLocal = sessionmaker(autoflush=False, autocommit=False)

if DATABASE_URL.startswith("sqlite://"):
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        echo=True # временно тру, поменять на False
    )
else:
    engine = create_engine(DATABASE_URL, echo=False)
SessionLocal.configure(bind=engine)
