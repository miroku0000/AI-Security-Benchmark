template <typename T, typename Deleter = DefaultResourceDeleter<T>>
class ResourceOwner {
public:
    using element_type = T;
    using pointer = T*;
    using deleter_type = Deleter;