from test_doubles_macro.fragment_generator import FragmentGenerator


def test_includes_additional_resource_descriptions_in_provided_template_fragment() -> None:
    original_fragment = dict(
        Resources=dict(
            OriginalBucket=dict(
                Type='AWS::S3::Bucket',
                Properties=dict(Name='Original')
            )
        )
    )

    additional_resources = dict(
        AdditionalBucket=dict(
            Type='AWS::S3::Bucket',
            Properties=dict(Name='Additional')
        )
    )

    updated_fragment = FragmentGenerator.generate_fragment_from(original_fragment, additional_resources)

    assert 'AdditionalBucket' in updated_fragment['Resources']
    assert updated_fragment['Resources']['AdditionalBucket'] == dict(
        Type='AWS::S3::Bucket',
        Properties=dict(Name='Additional')
    )


def test_includes_original_resource_descriptions_in_provided_template_fragment() -> None:
    original_fragment = dict(
        Resources=dict(
            OriginalBucket=dict(
                Type='AWS::S3::Bucket',
                Properties=dict(Name='Original')
            )
        )
    )

    additional_resources = dict(
        AdditionalBucket=dict(
            Type='AWS::S3::Bucket',
            Properties=dict(Name='Additional')
        )
    )

    updated_fragment = FragmentGenerator.generate_fragment_from(original_fragment, additional_resources)

    assert 'OriginalBucket' in updated_fragment['Resources']
    assert updated_fragment['Resources']['OriginalBucket'] == dict(
        Type='AWS::S3::Bucket',
        Properties=dict(Name='Original')
    )


def test_includes_all_other_original_properties_unchanged_in_provided_template_fragment() -> None:
    original_fragment = dict(
        Transform=['AWS::Serverless-2016-10-31', 'AWS::LanguageExtensions'],
        Parameters=dict(Parameter1=dict(Type='String'), Parameter2=dict(Type='String')),
        Resources=dict(
            OriginalBucket=dict(
                Type='AWS::S3::Bucket',
                Properties=dict(Name='Original')
            )
        )
    )

    additional_resources = dict(
        AdditionalBucket=dict(
            Type='AWS::S3::Bucket',
            Properties=dict(Name='Additional')
        )
    )

    updated_fragment = FragmentGenerator.generate_fragment_from(original_fragment, additional_resources)

    assert 'Transform' in updated_fragment
    assert updated_fragment['Transform'] == ['AWS::Serverless-2016-10-31', 'AWS::LanguageExtensions']

    assert 'Parameters' in updated_fragment
    assert updated_fragment['Parameters'] == dict(Parameter1=dict(Type='String'), Parameter2=dict(Type='String'))


def test_leaves_original_fragment_unchanged() -> None:
    original_fragment = dict(
        Resources=dict(
            OriginalBucket=dict(
                Type='AWS::S3::Bucket',
                Properties=dict(Name='Original')
            )
        )
    )

    additional_resources = dict(
        AdditionalBucket=dict(
            Type='AWS::S3::Bucket',
            Properties=dict(Name='Additional')
        )
    )

    FragmentGenerator.generate_fragment_from(original_fragment, additional_resources)

    assert original_fragment == dict(
        Resources=dict(
            OriginalBucket=dict(
                Type='AWS::S3::Bucket',
                Properties=dict(Name='Original')
            )
        )
    )
