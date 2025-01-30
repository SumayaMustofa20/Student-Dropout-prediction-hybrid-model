# -*- coding: utf-8 -*-
"""Student dropout prediction.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/12snyxc3k_5jP_5n6kTQygC_JrPkA-jrw
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.model_selection import KFold
from sklearn.feature_selection import RFE
from sklearn.metrics import mean_absolute_error as mae
from sklearn.metrics import mean_squared_error as mse
import matplotlib.pyplot as mtp
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import precision_score, recall_score, accuracy_score, f1_score, classification_report, confusion_matrix, ConfusionMatrixDisplay, PrecisionRecallDisplay, RocCurveDisplay
from sklearn.utils import resample

from tensorflow import keras
from tensorflow.keras.layers import Dropout
from tensorflow.keras.callbacks import EarlyStopping
from tensorflow.keras.optimizers import Adam

import warnings
warnings.filterwarnings('ignore')

df = pd.read_csv("/content/dataset.csv")
df

df['Target'].value_counts()

df['Target'] = LabelEncoder().fit_transform(df['Target'])

df['Target'].value_counts()

df.drop(df[df['Target'] == 1].index, inplace = True)
df

df['Dropout'] = df['Target'].apply(lambda x: 1 if x==0 else 0)
df

from sklearn.preprocessing import MinMaxScaler
x = df.iloc[:, :34].values
x = MinMaxScaler().fit_transform(x)
x
x.shape

y = df['Dropout'].values
y
y.shape

df['Target'].value_counts()

X_train, X_test, y_train, y_test = train_test_split(x, y, test_size=0.2, random_state=42, stratify=y)

train_data = pd.concat([pd.DataFrame(X_train), pd.DataFrame(y_train, columns=['target'])], axis=1)

# Separate minority and majority classes
majority = train_data[train_data.target == 0]
minority = train_data[train_data.target == 1]

# Upsample minority class
minority_upsampled = resample(minority,
                              replace=True,  # sample with replacement
                              n_samples=len(majority),  # match number in majority class
                              random_state=42)  # reproducible results

# Combine majority and upsampled minority
upsampled = pd.concat([majority, minority_upsampled])

# Separate features and target
X_train_balanced = upsampled.drop('target', axis=1).values
y_train_balanced = upsampled['target'].values

# Step 3: Cross-Validation Setup
k_fold = KFold(n_splits=5, shuffle=True, random_state=42)

# Placeholder for cross-validation predictions
all_y_test = []
all_y_pred = []

# Cross-validation loop
for train_index, val_index in k_fold.split(X_train_balanced, y_train_balanced):

    X_train_fold, X_val_fold = X_train_balanced[train_index], X_train_balanced[val_index]
    y_train_fold, y_val_fold = y_train_balanced[train_index], y_train_balanced[val_index]

    # Step 4: Feature Selection
    feature_selector = RFE(LogisticRegression())
    X_train_fold_selected = feature_selector.fit_transform(X_train_fold, y_train_fold)
    X_val_fold_selected = feature_selector.transform(X_val_fold)

    # Step 5: Standard Scaling
    scaler = StandardScaler()
    X_train_fold_scaled = scaler.fit_transform(X_train_fold_selected)
    X_val_fold_scaled = scaler.transform(X_val_fold_selected)

    # Step 6: Train Logistic Regression Model
    logistic_regression_model = LogisticRegression(random_state=42)
    logistic_regression_model.fit(X_train_fold_scaled, y_train_fold)

    # Step 7: Predict Probabilities using Logistic Regression Model
    y_prob_lr_train = logistic_regression_model.predict_proba(X_train_fold_scaled)[:, 1]
    y_prob_lr_val = logistic_regression_model.predict_proba(X_val_fold_scaled)[:, 1]

    # Step 8: Combine Logistic Regression Output with Original Features
    X_train_fold_combined = np.column_stack((X_train_fold_scaled, y_prob_lr_train))
    X_val_fold_combined = np.column_stack((X_val_fold_scaled, y_prob_lr_val))

    # Step 9: Define Neural Network Model
    input_dim_nn = X_train_fold_combined.shape[1]
    output_dim_nn = 2
    epochs_nn = 300
    batch_size_nn = 48
    validation_split_nn = 0.2

    model_nn = keras.Sequential([
        keras.layers.Dense(256, activation='sigmoid', input_shape=(input_dim_nn,), name='input_layer'),
        Dropout(0.5),
        keras.layers.Dense(128, activation='sigmoid', name='hidden_layer_1'),
        Dropout(0.5),
        keras.layers.Dense(64, activation='sigmoid', name='hidden_layer_2'),
        Dropout(0.5),
        keras.layers.Dense(64, activation='sigmoid', name='hidden_layer_3'),
        Dropout(0.5),
        keras.layers.Dense(32, activation='sigmoid', name='hidden_layer_4'),
        keras.layers.Dense(output_dim_nn, activation='softmax', name='output_layer')
    ])

    optimizer = Adam(learning_rate=0.001)

    # Compile the neural network model
    model_nn.compile(optimizer=optimizer, loss='sparse_categorical_crossentropy', metrics=['accuracy'])

    # Define EarlyStopping callback
    early_stopping = EarlyStopping(
        monitor='val_loss',
        patience=20,
        restore_best_weights=True
    )

    # Step 10: Train the Neural Network Model
    model_nn.fit(X_train_fold_combined, y_train_fold, epochs=epochs_nn, batch_size=batch_size_nn,
                 validation_split=validation_split_nn, callbacks=[early_stopping])

    # Step 11: Use the Trained Neural Network for Predictions
    y_pred_nnh = model_nn.predict(X_val_fold_combined)

    # Collect predictions
    y_pred_labels = np.argmax(y_pred_nnh, axis=1)
    all_y_test.extend(y_val_fold)  # Use extend to add elements to the list
    all_y_pred.extend(y_pred_labels)  # Use extend to add elements to the list

# Evaluate performance after cross-validation
all_y_test = np.array(all_y_test)  # Convert lists to numpy arrays for compatibility
all_y_pred = np.array(all_y_pred)
print(classification_report(all_y_test, all_y_pred))

# Final model training on the entire balanced training data
# Feature selection and scaling on the full training set
X_train_selected = feature_selector.fit_transform(X_train_balanced, y_train_balanced)
X_test_selected = feature_selector.transform(X_test)

X_train_scaled = scaler.fit_transform(X_train_selected)
X_test_scaled = scaler.transform(X_test_selected)

# Train Logistic Regression on the entire training data
logistic_regression_model.fit(X_train_scaled, y_train_balanced)
y_prob_lr_train_full = logistic_regression_model.predict_proba(X_train_scaled)[:, 1]
y_prob_lr_test_full = logistic_regression_model.predict_proba(X_test_scaled)[:, 1]

# Combine Logistic Regression Output with Original Features
X_train_combined_full = np.column_stack((X_train_scaled, y_prob_lr_train_full))
X_test_combined_full = np.column_stack((X_test_scaled, y_prob_lr_test_full))

# Define and train the final Neural Network Model on the combined features
model_nn_final = keras.Sequential([
    keras.layers.Dense(256, activation='sigmoid', input_shape=(X_train_combined_full.shape[1],), name='input_layer'),
    Dropout(0.5),
    keras.layers.Dense(128, activation='sigmoid', name='hidden_layer_1'),
    Dropout(0.5),
    keras.layers.Dense(64, activation='sigmoid', name='hidden_layer_2'),
    Dropout(0.5),
    keras.layers.Dense(64, activation='sigmoid', name='hidden_layer_3'),
    Dropout(0.5),
    keras.layers.Dense(32, activation='sigmoid', name='hidden_layer_4'),
    keras.layers.Dense(output_dim_nn, activation='softmax', name='output_layer')
])

model_nn_final.compile(optimizer=optimizer, loss='sparse_categorical_crossentropy', metrics=['accuracy'])

optimizer_final = Adam(learning_rate=0.001)
model_nn_final.compile(optimizer=optimizer_final, loss='sparse_categorical_crossentropy', metrics=['accuracy'])
optimizer_final.build(model_nn_final.trainable_variables)  # Build the optimizer with model's trainable variables

model_nn_final.fit(X_train_combined_full, y_train_balanced, epochs=epochs_nn, batch_size=batch_size_nn,
                   validation_split=validation_split_nn, callbacks=[early_stopping])

# Final predictions on the test set
y_test_pred_nnh = model_nn_final.predict(X_test_combined_full)
y_test_pred_labels = np.argmax(y_test_pred_nnh, axis=1)

# Final evaluation on the test set
print(classification_report(y_test, y_test_pred_labels))

model_nn.summary()

def perform(y_test,y_pred):
    print("Precision : ", precision_score(y_test, y_pred, average = 'micro'))
    print("Recall : ", recall_score(y_test, y_pred, average = 'micro'))
    print("Accuracy : ", accuracy_score(y_test, y_pred))
    print("F1 Score : ", f1_score(y_test, y_pred, average = 'micro'))
    cm = confusion_matrix(y_test, y_pred)
    print("\n", cm)
    print("\n")
    print("**"*27 + "\n" + " "* 16 + "Classification Report\n" + "**"*27)
    print(classification_report(y_test, y_pred))
    print("**"*27+"\n")

    cm = ConfusionMatrixDisplay(confusion_matrix = cm, display_labels=['Non-Dropout', 'Dropout'])
    cm.plot()

# Final evaluation on the test set
perform(y_test, y_test_pred_labels)

from sklearn.metrics import mean_absolute_error, mean_squared_error

# Calculate MAE and MSE
mae = mean_absolute_error(y_test, y_test_pred_labels)
mse = mean_squared_error(y_test, y_test_pred_labels)

# Calculate RAE (Relative Absolute Error)
rae = mae / np.mean(np.abs(y_test - np.mean(y_test)))

# Print the metrics
print(f"Mean Absolute Error (MAE): {mae:.2f}")
print(f"Mean Squared Error (MSE): {mse:.2f}")
print(f"Relative Absolute Error (RAE): {rae:.2f}")

fig, ax = plt.subplots()
plt.title("Precision-Recall Curve")
#PrecisionRecallDisplay.from_predictions(y_test, y_pred_nn, ax = ax, name = "NN", color='magenta')
PrecisionRecallDisplay.from_predictions(y_test, y_test_pred_labels, ax = ax, name = "HLRNN", color='green')

fig, ax = plt.subplots()
plt.title("ROC Curve")
RocCurveDisplay.from_predictions(y_test, y_test_pred_labels, ax = ax, name = "HLRNN", color='red')

!pip install shap lime

import shap

# Initialize the SHAP explainer
explainer = shap.KernelExplainer(model_nn_final.predict, X_train_combined_full[:100])  # Use a sample of data for speed

# Calculate SHAP values for the test data
shap_values = explainer.shap_values(X_test_combined_full[:100])  # Use a sample of data for visualization

# Plot the SHAP summary plot
shap.summary_plot(shap_values, X_test_combined_full[:100], feature_names=df.columns[:34].tolist() + ["LR Probability"])

import lime
from lime.lime_tabular import LimeTabularExplainer

# Initialize the LIME explainer
explainer = LimeTabularExplainer(X_train_combined_full, feature_names=df.columns[:34].tolist() + ["LR Probability"],
                                 class_names=['Non-Dropout', 'Dropout'], discretize_continuous=True)

# Choose a sample for explanation
sample_index = 0
sample = X_test_combined_full[sample_index]

# Generate the explanation for the sample
explanation = explainer.explain_instance(sample, model_nn_final.predict, num_features=10)

# Plot the LIME explanation
explanation.show_in_notebook(show_table=True)