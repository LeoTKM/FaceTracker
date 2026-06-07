from setuptools import find_packages, setup

package_name = 'face_tracker'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='feige',
    maintainer_email='leowang657@gmail.com',
    description='FaceTracker control package',
    license='Apache-2.0',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            'entry = face_tracker.entry:main',
            'i2c_manager = face_tracker.i2c_manager:main',
            'motor_joint = face_tracker.motor_joint:main',
            'camera = face_tracker.camera:main',
            'processor = face_tracker.processor:main'
        ],
    },
)
