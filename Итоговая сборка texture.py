# texture.py
import cv2
import numpy as np
from skimage.feature import graycomatrix, graycoprops
from skimage.color import rgb2gray
from skimage.util import img_as_ubyte
import pymysql
import os
import json
from PyQt6 import QtWidgets, QtCore

class Texture:
    """Класс для анализа текстурных характеристик изображения"""
    def __init__(self, image_path):
        self.image = cv2.imread(image_path)
        if self.image is None:
            raise ValueError("Не удалось загрузить изображение. Проверьте путь.")

    def get_texture(self):
        """Вычисление базовых текстурных характеристик"""
        gray_image = cv2.cvtColor(self.image, cv2.COLOR_BGR2GRAY)
        mean = np.mean(gray_image)
        variance = np.var(gray_image)
        std_dev = np.std(gray_image)
        return mean, variance, std_dev

class Laws:
    """Класс для анализа текстур по методу Laws"""
    @staticmethod
    def laws_kernels():
        L5 = np.array([1, 4, 6, 4, 1])
        E5 = np.array([-1, -2, 0, 2, 1])
        S5 = np.array([-1, 0, 2, 0, -1])
        R5 = np.array([1, -4, 6, -4, 1])
        W5 = np.array([-1, 2, 0, -2, 1])
        vectors = [L5, E5, S5, R5, W5]
        names = ['L5', 'E5', 'S5', 'R5', 'W5']
        filters = {}
        for i, vec1 in enumerate(vectors):
            for j, vec2 in enumerate(vectors):
                kernel = np.outer(vec1, vec2)
                filters[f"{names[i]}{names[j]}"] = kernel
        return filters

    @staticmethod
    def get_texture(image_path):
        image = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
        if image is None:
            raise ValueError("Не удалось загрузить изображение")

        image = image.astype(np.float32)
        image -= cv2.blur(image, (15, 15))

        kernels = Laws.laws_kernels()
        feature_vector = []
        for name, kernel in kernels.items():
            filtered = cv2.filter2D(image, -1, kernel)
            energy = np.mean(np.abs(filtered))
            feature_vector.append(energy)

        return np.array(feature_vector)

class GLCMAnalysis:
    """Класс для анализа текстур с помощью GLCM"""
    def __init__(self, image_path):
        self.image = cv2.imread(image_path)
        if self.image is None:
            raise ValueError("Не удалось загрузить изображение. Проверьте путь.")

    def calculate_entropy(self, glcm):
        glcm_normalized = glcm / np.sum(glcm)
        glcm_nonzero = glcm_normalized[glcm_normalized > 0]
        return -np.sum(glcm_nonzero * np.log2(glcm_nonzero))

    def get_texture(self, distances=[1], angles=[0]):
        gray_image = rgb2gray(self.image)
        gray_image = img_as_ubyte(gray_image)
        
        glcm = graycomatrix(gray_image, distances=distances, angles=angles, 
                          levels=256, symmetric=True, normed=False)
        
        contrast = graycoprops(glcm, 'contrast')[0, 0]
        energy = graycoprops(glcm, 'energy')[0, 0]
        homogeneity = graycoprops(glcm, 'homogeneity')[0, 0]
        entropy = self.calculate_entropy(glcm[:, :, 0, 0])
        
        return glcm[:, :, 0, 0], {
            'contrast': contrast,
            'energy': energy,
            'homogeneity': homogeneity,
            'entropy': entropy
        }

class Watershed_segmentation:
    """Класс для сегментации методом водоразделов"""
    def __init__(self, image_path):
        self.image = cv2.imread(image_path)
        if self.image is None:
            raise ValueError("Не удалось загрузить изображение. Проверьте путь.")

    def get_segmentation(self):
        image_gray = cv2.cvtColor(self.image, cv2.COLOR_BGR2GRAY)
        ret, thresh = cv2.threshold(image_gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        dist = cv2.distanceTransform(thresh, cv2.DIST_L2, 5) 
        ret, sure_fg = cv2.threshold(dist, 0.1 * dist.max(), 255, cv2.THRESH_BINARY) 
        sure_fg = sure_fg.astype(np.uint8)
        ret, markers = cv2.connectedComponents(sure_fg) 
        markers = cv2.watershed(self.image, markers)
        return markers

class Kmeans:
    """Класс для сегментации методом K-средних"""
    def __init__(self, image_path):
        self.image = cv2.imread(image_path)
        if self.image is None:
            raise ValueError("Не удалось загрузить изображение. Проверьте путь.")

    def get_segmentation(self):
        image_gray = cv2.cvtColor(self.image, cv2.COLOR_BGR2GRAY)
        pixel_values = image_gray.reshape((-1, 1)) 
        pixel_values = np.float32(pixel_values)
        criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 10, 1.0)
        k = 3
        _, labels, centers = cv2.kmeans(pixel_values, k, None, criteria, 10, cv2.KMEANS_RANDOM_CENTERS)
        centers = np.uint8(centers)
        segmented_image = centers[labels.flatten()] 
        segmented_image = segmented_image.reshape(image_gray.shape) 
        return segmented_image
