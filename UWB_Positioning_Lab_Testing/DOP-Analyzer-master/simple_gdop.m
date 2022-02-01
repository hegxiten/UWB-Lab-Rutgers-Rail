x_anchors = [0, 20, 20, 0];
y_anchors = [0, 0, 20, 20];
z_anchors = [0, 0, 0, 0];
anchors = [x_anchors; y_anchors; z_anchors];
x_tags = linspace(-5,25,150);
y_tags = linspace(-5,25,150);
z_tags = zeros(1,size(x_tags,2));
tags_true = [x_tags; y_tags; z_tags];

anchors_inv = anchors';
tags_inv = tags_true';
% GDOP =zeros(size(tags_inv,1),1);
% ranges = pdist2(anchors_inv, tags_inv, 'euclidean')';
% for x = 1:size(tags_inv,1) 
%     A =[anchors_inv - (repmat(tags_inv(x,:),size(anchors_inv,1), 1))./ranges(x,:)', -1*ones(size(anchors_inv,1),1)]; 
%     Q = pinv((A'*A));
%     GDOP(x)=sqrt(sum([Q(1,1),Q(2,2),Q(3,3)]));
% end

GDOP_mesh = [];

for i = 1:size(x_tags,2)
    tags_ori = [x_tags(i)*ones(1, size(y_tags,2)); y_tags; zeros(1,size(y_tags,2))];
    tags_inv_ = tags_ori';
    GDOP_ = zeros(size(tags_inv_,1),1);
    ranges_ = pdist2(anchors_inv, tags_inv_, 'euclidean')';
    for y = 1:size(tags_inv_,1)
        A_ =[anchors_inv - (repmat(tags_inv_(y,:),size(anchors_inv,1), 1))./ranges_(y,:)', -1*ones(size(anchors_inv,1),1)]; 
        Q_ = pinv((A_'*A_));
        GDOP_(y)=sqrt(sum([Q_(1,1),Q_(2,2),Q_(3,3)]));
    end
    GDOP_mesh = [GDOP_mesh, GDOP_];
end

[X, Y] = meshgrid(x_tags, y_tags);
contour(X, Y, GDOP_mesh)