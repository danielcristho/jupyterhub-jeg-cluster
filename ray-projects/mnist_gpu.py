import os
import tempfile
import numpy as np
import ray
from ray import serve
from starlette.requests import Request
from typing import Dict
import tensorflow as tf

TRAINED_MODEL_PATH = os.path.join(tempfile.gettempdir(), "mnist_model.h5")

ray.init("ray://10.21.73.122:10001", ignore_reinit_error=True, logging_level="debug", allow_multiple=True)
serve.start()


def train_and_save_model():
    """Train and save a simple MNIST model."""
    mnist = tf.keras.datasets.mnist
    (x_train, y_train), (x_test, y_test) = mnist.load_data()
    x_train, x_test = x_train / 255.0, x_test / 255.0

    model = tf.keras.models.Sequential(
        [
            tf.keras.layers.Flatten(input_shape=(28, 28)),
            tf.keras.layers.Dense(128, activation="relu"),
            tf.keras.layers.Dropout(0.2),
            tf.keras.layers.Dense(10),
        ]
    )
    model.compile(optimizer="adam", loss="sparse_categorical_crossentropy", metrics=["accuracy"])
    model.fit(x_train, y_train, epochs=1, verbose=1)

    model.save(TRAINED_MODEL_PATH)


if not os.path.exists(TRAINED_MODEL_PATH):
    train_and_save_model()


@serve.deployment(route_prefix="/predict")
class TFMnistModel:
    def __init__(self, model_path: str):
        """Load TensorFlow model."""
        self.model = tf.keras.models.load_model(model_path)

    async def __call__(self, request: Request) -> Dict:
        """Menerima input JSON, melakukan prediksi, dan mengembalikan hasil."""
        data = await request.json()
        input_array = np.array(data["array"]).reshape((1, 28, 28))

        prediction = self.model(input_array)
        return {"prediction": prediction.numpy().tolist()}


@serve.deployment(route_prefix="/health")
class HealthCheck:
    def __call__(self):
        return {"status": "ok"}


serve.run(TFMnistModel.bind(TRAINED_MODEL_PATH))
serve.run(HealthCheck.bind())