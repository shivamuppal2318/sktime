from copy import deepcopy
from sklearn.utils import check_random_state
from sktime.classification.deep_learning.base import BaseDeepClassifier
from sktime.networks.inceptiontime import InceptionTimeNetwork
from sktime.utils.dependencies import _check_dl_dependencies

# Ensure TensorFlow and Keras are imported correctly
import tensorflow as tf
from tensorflow import keras


class InceptionTimeClassifier(BaseDeepClassifier):
    """InceptionTime Deep Learning Classifier.

    Parameters
    ----------
    n_epochs : int, default=1500
    batch_size : int, default=64
        Number of samples per gradient update.
    kernel_size : int, default=40
        Length of the 1D convolution window.
    n_filters : int, default=32
    use_residual : bool, default=True
    use_bottleneck : bool, default=True
    bottleneck_size : int, default=32
    depth : int, default=6
    callbacks : list of tf.keras.callbacks.Callback objects, optional
    random_state : int, optional, default=None
        Random seed for internal random number generator.
    verbose : bool, default=False
        Whether to print runtime information.
    loss : str, default="categorical_crossentropy"
    metrics : list, optional
        List of metrics to be evaluated during training.

    Notes
    -----
    Based on Fawaz et. al, InceptionTime: Finding AlexNet for Time Series
    Classification, Data Mining and Knowledge Discovery, 34, 2020.
    Adapted from the implementation by Fawaz et. al:
    https://github.com/hfawaz/InceptionTime/blob/master/classifiers/inception.py
    """

    _tags = {
        "capability:multivariate": True,  # handles multivariate data
        "capability:unequal_length": False,  # does not handle unequal length
        "capability:missing_values": False,  # does not handle missing values
        "non-deterministic": True,  # due to random initialization
    }

    def __init__(
        self,
        n_epochs=1500,
        batch_size=64,
        kernel_size=40,
        n_filters=32,
        use_residual=True,
        use_bottleneck=True,
        bottleneck_size=32,
        depth=6,
        callbacks=None,
        random_state=None,
        verbose=False,
        loss="categorical_crossentropy",
        metrics=None,
    ):
        _check_dl_dependencies(severity="error")
        self.n_epochs = n_epochs
        self.batch_size = batch_size
        self.kernel_size = kernel_size
        self.n_filters = n_filters
        self.use_residual = use_residual
        self.use_bottleneck = use_bottleneck
        self.bottleneck_size = bottleneck_size
        self.depth = depth
        self.callbacks = callbacks
        self.random_state = random_state
        self.verbose = verbose
        self.loss = loss
        self.metrics = metrics or ["accuracy"]

        super().__init__()
        self._network = InceptionTimeNetwork(
            n_filters=n_filters,
            use_residual=use_residual,
            use_bottleneck=use_bottleneck,
            bottleneck_size=bottleneck_size,
            depth=depth,
            kernel_size=kernel_size,
            random_state=random_state,
        )

    def build_model(self, input_shape, n_classes):
        """Construct a compiled, untrained keras model."""
        input_layer, output_layer = self._network.build_network(input_shape)
        output_layer = keras.layers.Dense(n_classes, activation="softmax")(output_layer)
        model = keras.models.Model(inputs=input_layer, outputs=output_layer)
        model.compile(
            loss=self.loss,
            optimizer=keras.optimizers.Adam(),
            metrics=self.metrics,
        )
        return model

    def _fit(self, X, y):
        """Fit the classifier on the training set."""
        y_onehot = self._convert_y_to_keras(y)
        X = X.transpose(0, 2, 1)  # Conform to Keras input style.
        self.input_shape = X.shape[1:]
        self.model_ = self.build_model(self.input_shape, self.n_classes_)

        if self.verbose:
            self.model_.summary()

        callbacks = self._check_callbacks(self.callbacks)
        self.history = self.model_.fit(
            X,
            y_onehot,
            batch_size=self.batch_size,
            epochs=self.n_epochs,
            verbose=self.verbose,
            callbacks=deepcopy(callbacks),
        )
        return self

    def _check_callbacks(self, callbacks):
        """Check and configure default callbacks."""
        if callbacks is None:
            callbacks = []
        if not any(isinstance(cb, keras.callbacks.ReduceLROnPlateau) for cb in callbacks):
            callbacks.append(
                keras.callbacks.ReduceLROnPlateau(
                    monitor="loss", factor=0.5, patience=50, min_lr=1e-4
                )
            )
        return callbacks

    @classmethod
    def get_test_params(cls, parameter_set="default"):
        """Return testing parameter settings for the estimator."""
        param1 = {"n_epochs": 10, "batch_size": 4}
        param2 = {"n_epochs": 12, "batch_size": 6}
        return [param1, param2]