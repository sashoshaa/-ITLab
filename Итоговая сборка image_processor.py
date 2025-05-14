# image_processor.py
import cv2
import numpy as np
from skimage.feature import graycomatrix, graycoprops
from skimage.color import rgb2gray
from skimage.util import img_as_ubyte
import pymysql
import os
import json
from PyQt6 import QtWidgets, QtCore
from texture_lab import Texture, Laws, GLCMAnalysis, Watershed_segmentation, Kmeans

class ImageProcessor:
    """Основной класс для обработки изображений"""
    def __init__(self, parent=None):
        print("Используется ФИКСИРОВАННАЯ версия ImageProcessor v2.0")
        self.parent = parent
        self.current_dataset = "ImageData"
        
    def set_current_dataset(self, dataset_name):
        """Основной метод установки датасета"""
        self.current_dataset = dataset_name
        return self
    
    def calculate_color_features(self, image):
        """Вычисление цветовых характеристик изображения"""
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        
        # Гистограммы цветовых каналов
        hist_h = cv2.calcHist([hsv], [0], None, [256], [0, 256])
        hist_s = cv2.calcHist([hsv], [1], None, [256], [0, 256])
        hist_v = cv2.calcHist([hsv], [2], None, [256], [0, 256])
        
        # Разделение цветовых каналов
        (B, G, R) = cv2.split(image.astype("float"))
        
        # Вычисление цветности
        rg = np.absolute(R - G)
        yb = np.absolute(0.5 * (R + G) - B)
        std_root = np.sqrt((np.std(rg) ** 2) + (np.std(yb) ** 2))
        mean_root = np.sqrt((np.mean(rg) ** 2) + (np.mean(yb) ** 2))
        colorfulness = std_root + (0.3 * mean_root)
        
        return {
            'hue_mean': float(np.mean(hist_h)),
            'hue_std': float(np.std(hist_h)),
            'saturation_mean': float(np.mean(hist_s)),
            'saturation_std': float(np.std(hist_s)),
            'value_mean': float(np.mean(hist_v)),
            'value_std': float(np.std(hist_v)),
            'colorfulness': float(colorfulness)
        }
    def get_image_paths(self, image_id):
        """Возвращает пути к изображениям и маскам с правильными форматами имен"""
        if self.current_dataset == "imagedata2":
            # Формат для BloodSetGen: image_XXXX.jpg и mask_XXXX.jpg
            formatted_id = f"{image_id:04d}"  # 4 цифры с ведущими нулями
            image_name = f"image_{formatted_id}.jpg"
            mask_name = f"mask_{formatted_id}.jpg"
            image_path = os.path.normpath(f"D:/imagedata2/{image_name}")
            mask_path = os.path.normpath(f"D:/imagedata2/{mask_name}")
            return image_path, mask_path
        else:
            # Формат для основного датасета
            image_name = f"img_{image_id}.jpg"
            mask_name = f"mask_{image_id}.jpg"
            image_path = os.path.normpath(f"D:/dataset_egor_003_19/test/img/{image_name}")
            mask_path = os.path.normpath(f"D:/dataset_egor_003_19/test/mask/{mask_name}")
            return image_path, mask_path

    def calculate_metrics(self, image_path, mask_path=None):
        """Полный расчет всех характеристик с сегментацией"""
        metrics = {
            'image_name': os.path.basename(image_path),
            'mask_name': os.path.basename(mask_path) if mask_path else None,
            
            # Основные характеристики
            'image_mean': None,
            'image_variance': None,
            'image_std_dev': None,
            'image_laws': None,
            'image_glcm': None,
            'image_features': None,
            'mask_mean': None,
            'mask_variance': None,
            'mask_std_dev': None,
            'mask_laws': None,
            'mask_glcm': None,
            'mask_features': None,
            
            # Метрики сравнения
            'intersection_image_mask': None,
            'over_image_mask': None,
            'precision_image_mask': None,
            'recall_image_mask': None,
            'l1_metric_image_mask': None,
            
            # Метрики сегментации
            'intersection_watershed_mask': None,
            'over_watershed_mask': None,
            'precision_watershed_mask': None,
            'recall_watershed_mask': None,
            'l1_metric_watershed_mask': None,
            'intersection_kmeans_mask': None,
            'over_kmeans_mask': None,
            'precision_kmeans_mask': None,
            'recall_kmeans_mask': None,
            'l1_metric_kmeans_mask': None
        }

        try:
            # 1. Загрузка и обработка основного изображения
            image = cv2.imread(image_path)
            if image is None:
                raise ValueError(f"Не удалось загрузить изображение: {image_path}")
            
            gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Расчет характеристик изображения
            texture = Texture(image_path)
            metrics['image_mean'], metrics['image_variance'], metrics['image_std_dev'] = texture.get_texture()
            metrics['image_laws'] = ','.join(map(str, Laws.get_texture(image_path)))
            
            glcm_analysis = GLCMAnalysis(image_path)
            _, glcm_features = glcm_analysis.get_texture()
            metrics['image_glcm'] = json.dumps(glcm_features)
            metrics['image_features'] = json.dumps(self.calculate_color_features(image))

            # 2. Обработка маски
            mask = None
            if mask_path and os.path.exists(mask_path):
                mask = cv2.imread(mask_path, cv2.IMREAD_GRAYSCALE)
                if mask is not None:
                    _, binary_mask = cv2.threshold(mask, 127, 255, cv2.THRESH_BINARY)
                    
                    # Характеристики маски
                    texture_mask = Texture(mask_path)
                    metrics['mask_mean'], metrics['mask_variance'], metrics['mask_std_dev'] = texture_mask.get_texture()
                    metrics['mask_laws'] = ','.join(map(str, Laws.get_texture(mask_path)))
                    
                    glcm_mask = GLCMAnalysis(mask_path)
                    _, glcm_mask_features = glcm_mask.get_texture()
                    metrics['mask_glcm'] = json.dumps(glcm_mask_features)
                    metrics['mask_features'] = json.dumps(self.calculate_color_features(cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR)))

                    # Метрики сравнения
                    intersection = np.sum(np.minimum(gray_image, binary_mask))
                    over = np.sum(np.maximum(gray_image, binary_mask))
                    
                    true_pos = np.sum((binary_mask == 255) & (gray_image > 127))
                    false_pos = np.sum((binary_mask == 0) & (gray_image > 127))
                    false_neg = np.sum((binary_mask == 255) & (gray_image <= 127))
                    
                    precision = true_pos / (true_pos + false_pos + 1e-10)
                    recall = true_pos / (true_pos + false_neg + 1e-10)
                    l1_metric = np.mean(np.abs(binary_mask.astype(float) - gray_image.astype(float)/255.0))
                    
                    metrics.update({
                        'intersection_image_mask': int(intersection),
                        'over_image_mask': int(over),
                        'precision_image_mask': float(precision),
                        'recall_image_mask': float(recall),
                        'l1_metric_image_mask': float(l1_metric)
                    })

                    # 3. Методы сегментации
                    try:
                        # Watershed
                        w = Watershed_segmentation(image_path)
                        water = w.get_segmentation()
                        intersection_w = np.sum(np.minimum(water, binary_mask))
                        over_w = np.sum(np.maximum(water, binary_mask))
                        
                        metrics.update({
                            'intersection_watershed_mask': int(intersection_w),
                            'over_watershed_mask': int(over_w),
                            'precision_watershed_mask': float(precision),
                            'recall_watershed_mask': float(recall),
                            'l1_metric_watershed_mask': float(l1_metric)
                        })
                    except Exception as e:
                        print(f"Ошибка Watershed: {e}")

                    try:
                        # K-means
                        k = Kmeans(image_path)
                        km = k.get_segmentation()
                        intersection_k = np.sum(np.minimum(km, binary_mask))
                        over_k = np.sum(np.maximum(km, binary_mask))
                        
                        metrics.update({
                            'intersection_kmeans_mask': int(intersection_k),
                            'over_kmeans_mask': int(over_k),
                            'precision_kmeans_mask': float(precision),
                            'recall_kmeans_mask': float(recall),
                            'l1_metric_kmeans_mask': float(l1_metric)
                        })
                    except Exception as e:
                        print(f"Ошибка K-means: {e}")

        except Exception as e:
            print(f"Ошибка обработки {image_path}: {e}")

        return metrics

    def update_database(self, image_id):
        """Полное обновление всех характеристик в БД"""
        try:
            image_path, mask_path = self.get_image_paths(image_id)
            metrics = self.calculate_metrics(image_path, mask_path)
            
            conn = pymysql.connect(
                host="localhost",
                user="root",
                password="Dorogusha1",
                database="JupiterDB"
            )
            cursor = conn.cursor()

            update_query = f"""
            UPDATE {self.current_dataset} SET 
                image_name = %s,
                mask_name = %s,
                image_mean = %s,
                image_variance = %s,
                image_std_dev = %s,
                image_laws = %s,
                image_glcm = %s,
                image_features = %s,
                mask_mean = %s,
                mask_variance = %s,
                mask_std_dev = %s,
                mask_laws = %s,
                mask_glcm = %s,
                mask_features = %s,
                intersection_image_mask = %s,
                over_image_mask = %s,
                precision_image_mask = %s,
                recall_image_mask = %s,
                l1_metric_image_mask = %s,
                intersection_watershed_mask = %s,
                over_watershed_mask = %s,
                precision_watershed_mask = %s,
                recall_watershed_mask = %s,
                l1_metric_watershed_mask = %s,
                intersection_kmeans_mask = %s,
                over_kmeans_mask = %s,
                precision_kmeans_mask = %s,
                recall_kmeans_mask = %s,
                l1_metric_kmeans_mask = %s
            WHERE id = %s
            """
            
            params = (
                metrics['image_name'],
                metrics['mask_name'],
                metrics['image_mean'],
                metrics['image_variance'],
                metrics['image_std_dev'],
                metrics['image_laws'],
                metrics['image_glcm'],
                metrics['image_features'],
                metrics['mask_mean'],
                metrics['mask_variance'],
                metrics['mask_std_dev'],
                metrics['mask_laws'],
                metrics['mask_glcm'],
                metrics['mask_features'],
                metrics['intersection_image_mask'],
                metrics['over_image_mask'],
                metrics['precision_image_mask'],
                metrics['recall_image_mask'],
                metrics['l1_metric_image_mask'],
                metrics['intersection_watershed_mask'],
                metrics['over_watershed_mask'],
                metrics['precision_watershed_mask'],
                metrics['recall_watershed_mask'],
                metrics['l1_metric_watershed_mask'],
                metrics['intersection_kmeans_mask'],
                metrics['over_kmeans_mask'],
                metrics['precision_kmeans_mask'],
                metrics['recall_kmeans_mask'],
                metrics['l1_metric_kmeans_mask'],
                image_id
            )

            cursor.execute(update_query, params)
            conn.commit()
            return True

        except Exception as e:
            print(f"Ошибка БД: {e}")
            if 'conn' in locals():
                conn.rollback()
            return False
        finally:
            if 'conn' in locals():
                conn.close()

    def process_new_images(self):
        """Обработка всех новых изображений для текущего датасета"""
        try:
            conn = pymysql.connect(
                host="localhost",
                user="root",
                password="Dorogusha1",
                database="JupiterDB"
            )
            cursor = conn.cursor()
            
            # Унифицированный запрос для обоих датасетов
            cursor.execute(f"SELECT id FROM {self.current_dataset} WHERE image_mean IS NULL")
            image_ids = [row[0] for row in cursor.fetchall()]
            conn.close()

            if not image_ids:
                QtWidgets.QMessageBox.information(self.parent, "Информация", "Нет новых изображений для обработки")
                return False

            progress = QtWidgets.QProgressDialog(
                "Обработка изображений...", 
                "Отмена", 
                0, 
                len(image_ids), 
                self.parent
            )
            progress.setWindowModality(QtCore.Qt.WindowModality.WindowModal)
            progress.show()

            success_count = 0
            for i, image_id in enumerate(image_ids):
                progress.setValue(i)
                QtWidgets.QApplication.processEvents()
                
                if progress.wasCanceled():
                    break
                
                if self.update_database(image_id):
                    success_count += 1

            progress.close()

            result_msg = f"""Обработка завершена:
            Всего изображений: {len(image_ids)}
            Успешно обработано: {success_count}
            Ошибок: {len(image_ids) - success_count}"""
            
            QtWidgets.QMessageBox.information(self.parent, "Результат", result_msg)
            return True

        except Exception as e:
            QtWidgets.QMessageBox.critical(self.parent, "Ошибка", f"Ошибка при обработке: {str(e)}")
            return False
