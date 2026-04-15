#include <utility>
#include <cstddef>

template<typename T>
class ResourceManager {
private:
    T* resource_;
    
public:
    explicit ResourceManager(T* resource = nullptr) noexcept 
        : resource_(resource) {}
    
    ~ResourceManager() {
        delete resource_;
    }
    
    ResourceManager(const ResourceManager&) = delete;
    ResourceManager& operator=(const ResourceManager&) = delete;
    
    ResourceManager(ResourceManager&& other) noexcept 
        : resource_(other.resource_) {
        other.resource_ = nullptr;
    }
    
    ResourceManager& operator=(ResourceManager&& other) noexcept {
        if (this != &other) {
            delete resource_;
            resource_ = other.resource_;
            other.resource_ = nullptr;
        }
        return *this;
    }
    
    void reset(T* new_resource = nullptr) {
        if (resource_ != new_resource) {
            delete resource_;
            resource_ = new_resource;
        }
    }
    
    T* release() noexcept {
        T* temp = resource_;
        resource_ = nullptr;
        return temp;
    }
    
    T* get() const noexcept {
        return resource_;
    }
    
    T& operator*() const {
        return *resource_;
    }
    
    T* operator->() const noexcept {
        return resource_;
    }
    
    explicit operator bool() const noexcept {
        return resource_ != nullptr;
    }
    
    void swap(ResourceManager& other) noexcept {
        std::swap(resource_, other.resource_);
    }
};

template<typename T>
void swap(ResourceManager<T>& lhs, ResourceManager<T>& rhs) noexcept {
    lhs.swap(rhs);
}

template<typename T, typename... Args>
ResourceManager<T> make_resource(Args&&... args) {
    return ResourceManager<T>(new T(std::forward<Args>(args)...));
}