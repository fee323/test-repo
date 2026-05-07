from environment import before_feature
from selenium.webdriver import Chrome


class MockContext:
    driver: Chrome

before_feature(MockContext(), 'Launching Browser')
